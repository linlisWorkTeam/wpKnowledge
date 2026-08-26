"""知识飞轮编排层（确定性状态机）。

对应《知识飞轮实现方案.md》§2/§3 与《codeagent执行手册》：
- 固定流水线 + 文件交接 + 编排层状态机
- 每轮：知识生成 → Coder 写码 → 评测闭环 → Review 归因 → 决策（通过/迭代/回滚）
- 信息隔离：Coder 不读源码（桩内不传 src）
- 写保护：知识库路径受保护（MVP 简化：只写 storage/）
"""

import json
import shutil
from dataclasses import asdict
from pathlib import Path

from eval import detect_format, evaluate, evaluate_native, find_native_tests, load_cases
from eval.holdout import split_cases
from fw.config import Config
from revise import CorrectionQueue, decide
from roles import EvalReport, KnowledgeDoc
from roles.stubs import StubCoder, StubKnowledgeGen, StubReview


class KnowledgeFlywheel:
    """知识飞轮主循环。"""

    def __init__(self, cfg: Config,
                 knowledge_gen=None, coder=None, review=None):
        self.cfg = cfg
        self.knowledge_gen = knowledge_gen or StubKnowledgeGen()
        self.coder = coder or StubCoder()
        self.review = review or StubReview()
        self.queue = CorrectionQueue(cfg)
        self.history = []          # 每轮 (round, report, decision)
        self._round = 0

    # ---------- 主循环 ----------

    def run(self, module: str, src_file: Path, report_dir: Path | None = None) -> dict:
        """跑一次完整飞轮：知识 → 代码 → 评测 → 归因 → 修订 → 重测。

        返回 {doc, code_path, reports, decision, rounds, holdout_report}。
        """
        report_dir = report_dir or (self.cfg.work_dir / "reports")
        report_dir.mkdir(parents=True, exist_ok=True)

        # 0. 检测评测集格式并加载
        fmt = detect_format(self.cfg.evalset_dir, self.cfg)
        if fmt == "native":
            # 原生测试文件模式：用户本地测试集，直接编译运行
            test_files = find_native_tests(self.cfg.evalset_dir, self.cfg, module)
            if not test_files:
                raise FileNotFoundError(
                    f"评测集目录 {self.cfg.evalset_dir} 无匹配测试文件 "
                    f"(glob: {self.cfg.native_test_glob})")
            train_cases, holdout_cases = test_files, []
            # native 模式不做 holdout 切分（本地测试集整体作为评测信号，防止误切）
            eval_fn = evaluate_native
        else:
            # JSON cases 模式
            all_cases = [c for c in load_cases(self.cfg.evalset_dir)
                         if c.get("module") == module]
            splits = split_cases(all_cases, self.cfg.holdout_ratio)
            train_cases = splits["train"]
            holdout_cases = splits["holdout"]
            eval_fn = evaluate

        # 1. 首版知识生成（唯一执笔者）
        sources = [{"file": str(src_file), "symbol": module, "lines": "0-0"}]
        doc = self.knowledge_gen.generate(module, src_file, sources)
        self._save_knowledge(doc)  # v1 落盘，中间产物可核查

        prev_confidence = None
        decision = "iterate"
        last_report = None
        code_path = None

        for r in range(1, self.cfg.max_rounds + 1):
            self._round = r
            # 2. Coder 写码（信息隔离：只传知识，不传源码）
            code_path = self.cfg.work_dir / "traces" / f"{module}_r{r}.c"
            code_path = self.coder.generate_code(doc, code_path)

            # 3. 评测闭环（train 集）
            src_text = src_file.read_text() if src_file.exists() else ""
            report = eval_fn(module, code_path, train_cases, self.cfg,
                             src_text=src_text, work_dir=self.cfg.work_dir / "traces")
            last_report = report

            # 4. Review 归因
            attribution = self.review.attribute(module, doc, report)

            # 5. 决策
            decision = decide(report, prev_confidence, self.cfg)
            prev_confidence = report.confidence
            self.history.append({"round": r, "confidence": report.confidence,
                                 "compile_ok": report.compile_ok, "decision": decision,
                                 "variance": report.reps_variance,
                                 "unstable": report.unstable})

            self._save_report(report_dir, r, report, attribution, decision)

            if decision == "pass":
                doc.status = "verified"
                break
            if decision == "rollback":
                # 回滚：恢复到上一版知识（MVP：回到 v1）
                doc = KnowledgeDoc(module=module, content=doc.content, sources=doc.sources,
                                   version=max(1, doc.version - 1))
                break

            # 6. 迭代：入队列 + 修订（版本 +1）
            self.queue.push(attribution)
            from revise import apply_revision
            doc = apply_revision(doc, self.queue.pop_pending(), self.knowledge_gen.revise)
            self.queue.clear()
            self._save_knowledge(doc)  # 修订后版本立即落盘

        # holdout 评测（JSON 模式：只报告，不写回；native 模式：无 holdout）
        holdout_report = None
        if holdout_cases and code_path:
            if fmt == "native":
                holdout_report = None
            else:
                holdout_report = evaluate(module, code_path, holdout_cases, self.cfg,
                                          src_text=src_file.read_text() if src_file.exists() else "",
                                          work_dir=self.cfg.work_dir / "traces")

        self._save_knowledge(doc)
        return {
            "doc": doc,
            "code_path": code_path,
            "train_report": last_report,
            "holdout_report": holdout_report,
            "decision": decision,
            "rounds": self._round,
            "history": self.history,
        }

    # ---------- 持久化 ----------

    def _save_report(self, report_dir: Path, r: int, report: EvalReport,
                     attribution, decision: str):
        payload = {
            "round": r,
            "module": report.module,
            "compile_ok": report.compile_ok,
            "compile_errors": report.compile_errors[:5],
            "passed": report.passed,
            "total": report.total,
            "confidence": report.confidence,
            "reps": {"count": report.reps_count, "mean": report.reps_mean,
                     "variance": report.reps_variance, "min": report.reps_min,
                     "unstable": report.unstable},
            "similarity": report.similarity,
            "decision": decision,
            "attribution": attribution.summary,
            "weak_spots": attribution.weak_spots,
        }
        (report_dir / f"round_{r}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2))

    def _save_knowledge(self, doc: KnowledgeDoc):
        out = self.cfg.knowledge_dir / f"{doc.module}_v{doc.version}.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(doc.content)
        # 写保护（MVP 简化）：记录知识库文件哈希
        self._write_protection_log()

    def _write_protection_log(self):
        import hashlib
        log = {}
        for f in (self.cfg.knowledge_dir).glob("*.md"):
            log[f.name] = hashlib.sha256(f.read_bytes()).hexdigest()[:16]
        (self.cfg.work_dir / "protection.json").write_text(
            json.dumps(log, indent=2))
