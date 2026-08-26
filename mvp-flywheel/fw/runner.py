"""知识飞轮确定性编排层。"""

import hashlib
import json
import subprocess
import time
import uuid
from pathlib import Path

from eval import (aggregate_generation_reports, detect_format, evaluate,
                  evaluate_native, find_native_tests, load_cases)
from eval.holdout import split_cases
from fw.config import Config, ConfigError
from fw.protection import ProtectionMismatch, snapshot, verify, write_snapshot
from revise import CorrectionQueue, apply_revision, decide
from roles import Attribution, EvalReport, KnowledgeDoc
from roles.stubs import StubCoder, StubKnowledgeGen, StubReview


class KnowledgeLeakError(RuntimeError):
    pass


class KnowledgeFlywheel:
    def __init__(self, cfg: Config, knowledge_gen=None, coder=None, review=None):
        self.cfg = cfg.validate()
        self.knowledge_gen = knowledge_gen or StubKnowledgeGen()
        self.coder = coder or StubCoder()
        self.review = review or StubReview()
        if cfg.production and any(isinstance(role, (StubKnowledgeGen, StubCoder, StubReview))
                                  for role in (self.knowledge_gen, self.coder, self.review)):
            raise ConfigError("production 模式禁止使用 Stub 角色")
        self.history = []
        self._round = 0

    def run(self, module: str, src_file: Path, report_dir: Path | None = None,
            initial_doc: KnowledgeDoc | None = None) -> dict:
        """执行有界飞轮；只有通过 train 与所需 holdout 后才发布知识。"""
        started = time.monotonic()
        self.history = []
        self._round = 0
        src_file = Path(src_file).resolve()
        run_id = uuid.uuid4().hex
        run_root = self.cfg.work_dir / "runs" / run_id
        private_reports = Path(report_dir) if report_dir else run_root / "eval"
        for directory in (run_root / "knowledge", run_root / "code", private_reports,
                          run_root / "attribution", run_root / "corrections", run_root / "protection"):
            directory.mkdir(parents=True, exist_ok=True)

        self._write_config_snapshot(run_root, run_id)
        protected_paths = self._protected_paths()
        before = snapshot(protected_paths)
        self._protection_before = before
        write_snapshot(run_root / "protection/before.json", before)

        fmt, train_items, holdout_items = self._load_eval_items(module)
        source_text = src_file.read_text(encoding="utf-8") if src_file.exists() else ""
        source_commit = self.cfg.source_commit or "sha256:" + hashlib.sha256(
            source_text.encode("utf-8")).hexdigest()
        sources = [{
            "file": str(src_file),
            "symbol": module,
            "lines": "display-only",
            "commit": source_commit,
        }]

        if initial_doc is None:
            doc = self.knowledge_gen.generate(module, src_file, sources)
        else:
            doc = initial_doc.clone()
        doc = doc.clone(module=module, source_commit=source_commit, run_id=run_id, status="draft")
        if self.cfg.production:
            assert_no_source_leak(doc.content, source_text)
        verify(before, protected_paths)
        self._save_candidate(run_root, doc)

        queue = CorrectionQueue(self.cfg, run_id=run_id)
        doc_history = [doc.clone()]
        prev_confidence = None
        pending_ids = []
        decision = "iterate"
        last_report = None
        holdout_report = None
        code_paths = []

        for round_number in range(1, self.cfg.max_rounds + 1):
            self._round = round_number
            reports, code_paths = self._generate_and_evaluate(
                module, doc, src_file, source_text, fmt, train_items, run_root, round_number
            )
            budget_exhausted = round_number >= self.cfg.max_rounds or self._time_exhausted(started)
            report = aggregate_generation_reports(reports, self.cfg, "train")
            self._annotate_report(report, doc, run_id, round_number, "train")
            last_report = report

            public_report = report.public_copy()
            attribution = self.review.attribute(module, doc.clone(), public_report)
            verify(before, protected_paths)

            decision = decide(report, prev_confidence, self.cfg, budget_exhausted=budget_exhausted)
            report.decision = decision
            prev_confidence = report.confidence
            report_path = self._save_report(private_reports, report, attribution)
            self._save_attribution(run_root, round_number, attribution)

            if pending_ids:
                for correction_id in pending_ids:
                    queue.mark_done(correction_id, ok=decision == "pass", evidence=[str(report_path)])
                pending_ids = []

            self.history.append({
                "round": round_number,
                "confidence": report.confidence,
                "compile_ok": report.compile_ok,
                "decision": decision,
                "variance": report.reps_variance,
                "unstable": report.unstable,
                "reason_codes": list(report.reason_codes),
            })

            if decision == "pass":
                holdout_report = self._evaluate_holdout(
                    module, code_paths, source_text, fmt, holdout_items, run_root, doc, run_id, round_number
                )
                if holdout_report is None:
                    if self.cfg.require_holdout:
                        decision = "stopped"
                        report.reason_codes.append("HOLDOUT_REQUIRED")
                    else:
                        decision = "pass"
                elif holdout_report.passes(self.cfg.pass_threshold):
                    decision = "pass"
                else:
                    decision = "stopped"
                    report.reason_codes.append("HOLDOUT_BELOW_THRESHOLD")
                report.decision = decision
                self.history[-1]["decision"] = decision
                self._save_report(private_reports, report, attribution)
                if decision == "pass":
                    doc = doc.clone(status="verified")
                    self._publish_knowledge(doc)
                    self._protection_before = snapshot(protected_paths)
                break

            if decision == "rollback":
                doc = doc_history[-2].clone() if len(doc_history) >= 2 else doc_history[0].clone()
                doc = doc.clone(status="draft")
                break
            if decision == "stopped":
                break

            if not attribution.corrections:
                decision = "stopped"
                report.decision = decision
                report.reason_codes.append("INCOMPLETE_FEEDBACK")
                self.history[-1]["decision"] = decision
                break

            queue.push(attribution, round_number=round_number, knowledge_version=doc.version)
            pending_ids = [correction.id for correction in attribution.corrections]
            doc = apply_revision(doc, attribution.corrections, self.knowledge_gen.revise)
            doc = doc.clone(run_id=run_id, source_commit=source_commit)
            if self.cfg.production:
                assert_no_source_leak(doc.content, source_text)
            verify(before, protected_paths)
            doc_history.append(doc.clone())
            self._save_candidate(run_root, doc)

        after = verify(self._protection_before, protected_paths)
        write_snapshot(run_root / "protection/after.json", after)
        result = {
            "schema_version": "flywheel-result.v1",
            "run_id": run_id,
            "doc": doc,
            "code_path": code_paths[0] if code_paths else None,
            "code_paths": code_paths,
            "train_report": last_report,
            "holdout_report": holdout_report,
            "decision": decision,
            "rounds": self._round,
            "history": self.history,
            "run_root": run_root,
        }
        self._save_result(run_root, result)
        return result

    def _load_eval_items(self, module: str):
        eval_root = self.cfg.private_evalset_dir or self.cfg.evalset_dir
        fmt = detect_format(eval_root, self.cfg)
        if fmt == "native":
            train_root = eval_root / "train"
            holdout_root = eval_root / "holdout"
            if not train_root.exists():
                train_root = eval_root
            train = find_native_tests(train_root, self.cfg, module)
            holdout = find_native_tests(holdout_root, self.cfg, module) if holdout_root.exists() else []
            return fmt, train, holdout
        cases = [case for case in load_cases(eval_root) if case.get("module") == module]
        splits = split_cases(cases, self.cfg.holdout_ratio)
        return fmt, splits["train"], splits["holdout"]

    def _generate_and_evaluate(self, module, doc, src_file, source_text, fmt,
                               train_items, run_root, round_number):
        reports, paths = [], []
        extension = src_file.suffix if src_file.suffix in {".c", ".cc", ".cpp", ".cxx"} else ".cpp"
        eval_fn = evaluate_native if fmt == "native" else evaluate
        for generation in range(1, self.cfg.repeat_generation + 1):
            code_path = run_root / "code" / f"round_{round_number:03d}_g{generation:03d}{extension}"
            produced = self.coder.generate_code(doc.clone(), code_path)
            verify(self._protection_before, self._protected_paths())
            report = eval_fn(module, produced, train_items, self.cfg, src_text=source_text,
                             work_dir=run_root / "eval-work" / f"r{round_number}_g{generation}")
            reports.append(report)
            paths.append(produced)
        return reports, paths

    def _evaluate_holdout(self, module, code_paths, source_text, fmt, holdout_items,
                          run_root, doc, run_id, round_number):
        if not holdout_items:
            return None
        eval_fn = evaluate_native if fmt == "native" else evaluate
        reports = []
        for generation, code_path in enumerate(code_paths, 1):
            report = eval_fn(module, code_path, holdout_items, self.cfg, src_text=source_text,
                             work_dir=run_root / "eval-work" / f"holdout_g{generation}")
            reports.append(report)
        aggregate = aggregate_generation_reports(reports, self.cfg, "holdout")
        self._annotate_report(aggregate, doc, run_id, round_number, "holdout")
        aggregate.decision = "pass" if aggregate.passes(self.cfg.pass_threshold) else "stopped"
        # 私有明细仅写入受控 run 目录，不交给任何生成角色。
        path = run_root / "eval" / "holdout_final.json"
        path.write_text(json.dumps(aggregate.as_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return aggregate.public_copy()

    def _annotate_report(self, report, doc, run_id, round_number, split):
        report.run_id = run_id
        report.round = round_number
        report.split = split
        report.knowledge_version = doc.version
        report.knowledge_sha256 = doc.sha256
        report.evalset_version = self.cfg.evalset_version
        report.source_commit = doc.source_commit
        report.environment = {
            "compiler": self.cfg.compiler,
            "compiler_version": self._compiler_version(),
            "flags": self.cfg.compile_flags,
            "model": self.cfg.model_id,
            "provider": self.cfg.model_provider,
            "prompt_version": self.cfg.prompt_version,
        }
        # EVAL-008 探针证据：期望输出来源必须可追溯（探针/人工推导），禁止 LLM 编造
        report.probe_evidence = {
            "provenance": "probe",
            "source_commit": doc.source_commit,
            "evalset_version": self.cfg.evalset_version,
            "note": "期望输出必须来自探针运行真实源码或明确的人工推导依据；"
                    "若为人工推导须在评测集 manifest 的 golden_note 中说明",
        }

    def _save_report(self, report_dir, report, attribution):
        payload = report.as_dict()
        payload["attribution"] = {
            "summary": attribution.summary,
            "weak_spots": attribution.weak_spots,
            "corrections": [correction.__dict__ for correction in attribution.corrections],
        }
        path = report_dir / f"train_round_{report.round:03d}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def _save_attribution(self, run_root, round_number, attribution):
        path = run_root / "attribution" / f"round_{round_number:03d}.json"
        payload = {
            "module": attribution.module,
            "summary": attribution.summary,
            "weak_spots": attribution.weak_spots,
            "corrections": [correction.__dict__ for correction in attribution.corrections],
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _save_candidate(self, run_root, doc):
        path = run_root / "knowledge" / f"{doc.module}_v{doc.version}.md"
        path.write_text(doc.render(), encoding="utf-8")

    def _publish_knowledge(self, doc):
        self.cfg.knowledge_dir.mkdir(parents=True, exist_ok=True)
        path = self.cfg.knowledge_dir / f"{doc.module}_v{doc.version}.md"
        path.write_text(doc.render(), encoding="utf-8")

    def _write_config_snapshot(self, run_root, run_id):
        def encode(value):
            if isinstance(value, Path):
                return str(value)
            if isinstance(value, list):
                return [encode(item) for item in value]
            return value
        payload = {name: encode(value) for name, value in vars(self.cfg).items()}
        payload["run_id"] = run_id
        (run_root / "config.snapshot.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _save_result(self, run_root, result):
        payload = {
            "schema_version": result["schema_version"],
            "run_id": result["run_id"],
            "decision": result["decision"],
            "rounds": result["rounds"],
            "knowledge": {
                "module": result["doc"].module,
                "version": result["doc"].version,
                "status": result["doc"].status,
                "sha256": result["doc"].sha256,
            },
            "history": result["history"],
        }
        (run_root / "result.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _protected_paths(self):
        paths = [self.cfg.src_dir, self.cfg.evalset_dir, self.cfg.knowledge_dir]
        if self.cfg.interfaces_dir is not None:
            paths.append(self.cfg.interfaces_dir)
        if self.cfg.private_evalset_dir is not None:
            paths.append(self.cfg.private_evalset_dir)
        paths.extend(self.cfg.protected_paths)
        return paths

    def _compiler_version(self):
        try:
            proc = subprocess.run([self.cfg.compiler, "--version"], capture_output=True,
                                  text=True, timeout=10, encoding="utf-8", errors="replace")
            return proc.stdout.splitlines()[0] if proc.stdout else "unknown"
        except (OSError, subprocess.TimeoutExpired):
            return "unavailable"

    def _time_exhausted(self, started):
        return self.cfg.max_seconds is not None and time.monotonic() - started >= self.cfg.max_seconds


def assert_no_source_leak(knowledge: str, source: str) -> None:
    """确定性红线：禁止知识包含连续的源码实现行。"""
    knowledge_compact = " ".join(knowledge.split())
    suspicious = []
    for line in source.splitlines():
        stripped = " ".join(line.strip().split())
        if len(stripped) >= 30 and not stripped.startswith(("//", "/*", "*", "#include")):
            if stripped in knowledge_compact:
                suspicious.append(stripped)
    if suspicious:
        raise KnowledgeLeakError("知识包含源码实现片段: " + suspicious[0][:160])
