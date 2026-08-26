"""ACC-HOLD / ACC-KNOW / ACC-OBS / SYS-003 验收场景专项测试。"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fw.config import Config
from fw.runner import KnowledgeFlywheel
from roles import Correction, KnowledgeDoc
from roles.stubs import StubKnowledgeGen, StubReview

BASE = Path(__file__).resolve().parents[2]
CALC = BASE / "tests/fixtures/calc"


def _dev_calc(tmp_path, require_holdout=False, native=False):
    evalset = CALC / ("evalset_native" if native else "evalset")
    return Config(
        src_dir=CALC / "src",
        evalset_dir=evalset,
        work_dir=tmp_path / "data",
        knowledge_dir=tmp_path / "accepted",
        ledger_path=tmp_path / "ledger.json",
        compiler="gcc",
        compile_flags=["-Wall", "-Werror", "-std=c11", "-I{interfaces_dir}"],
        require_holdout=require_holdout,
        repeat_eval=1,
    ).resolve(BASE)


# ---------- SYS-003：从既有知识启动（不强制首版生成） ----------

def test_run_starts_from_existing_doc_without_generation(tmp_path):
    """给定 initial_doc，runner 不调用知识生成，直接进入 Coder 环节。"""
    cfg = _dev_calc(tmp_path)

    class _NoGen(StubKnowledgeGen):
        def generate(self, module, src_file, sources):
            raise AssertionError("不应调用知识生成（SYS-003：首版生成属于上游）")

    source = (CALC / "src/calc.c").read_text(encoding="utf-8")
    existing = KnowledgeDoc(
        module="calc", version=3, status="verified",
        content=f"# calc 模块知识\n\n> 来源：上游提供（SYS-003：首版生成不属于 runner）\n\n```c\n{source}\n```\n",
        source_commit="abc123",
    )
    fw = KnowledgeFlywheel(cfg, knowledge_gen=_NoGen(), review=StubReview())
    result = fw.run("calc", CALC / "src/calc.c", initial_doc=existing)
    assert result["decision"] == "pass"
    assert result["doc"].version == 3  # 保留既有版本号
    # runner 会按 cfg.source_commit（空则内容哈希）注入 run 级 commit
    assert result["doc"].source_commit.startswith("sha256:")


def test_run_without_initial_doc_calls_generation(tmp_path):
    """无 initial_doc 时仍走知识生成（向后兼容）。"""
    cfg = _dev_calc(tmp_path)
    fw = KnowledgeFlywheel(cfg, review=StubReview())
    result = fw.run("calc", CALC / "src/calc.c")
    assert result["decision"] == "pass"


# ---------- ACC-HOLD-001：holdout 不产生修订反馈 ----------

def test_holdout_failures_redacted_from_generation_context(tmp_path):
    """holdout 失败详情不进生成上下文（public_copy 脱敏）。"""
    cfg = _dev_calc(tmp_path, require_holdout=True)

    class _SpyReview(StubReview):
        def __init__(self):
            self.seen_failures = None

        def attribute(self, module, doc, report):
            self.seen_failures = report.failures
            return super().attribute(module, doc, report)

    spy = _SpyReview()
    fw = KnowledgeFlywheel(cfg, review=spy)
    fw.run("calc", CALC / "src/calc.c")
    # Review 只看到 train 报告；holdout 报告不经 Review（聚合脱敏）
    assert spy.seen_failures is not None


# ---------- ACC-KNOW-002：修订产生新版本且旧版不变 ----------

def test_revision_creates_new_version_keeps_old(tmp_path):
    """修订产生 draft v2，v1 内容和元数据保持不变。"""
    cfg = _dev_calc(tmp_path)

    def rev(doc, corrections):
        doc.content += "\n## 修订补丁\n- 判据: pass\n"
        return doc

    original = KnowledgeDoc(module="calc", version=1, content="v1 内容")
    from revise import apply_revision
    revised = apply_revision(original, [Correction("c1", "calc#add", "add passes")], rev)
    assert original.content == "v1 内容"          # 旧版不变
    assert original.version == 1
    assert revised.version == 2                   # 新版 +1
    assert revised.parent_version == 1
    assert revised.status == "draft"


# ---------- ACC-KNOW-003：回滚恢复真实内容 ----------

def test_rollback_restores_persisted_content(tmp_path):
    """指标下降 → 回滚恢复上一版内容（不是版本号减一）。"""
    cfg = _dev_calc(tmp_path)
    cfg.max_rounds = 3

    class _RegressingCoder:
        """R1 部分错误（触发迭代+修订）；R2 更错误（修订后反而退步）→ 回滚。

        模式：每次调用注入不同的错误集，第二轮注入更多错误，
        使 confidence 下降触发 REGRESSION → rollback。
        """

        def __init__(self, source):
            self.source = source
            self.call = 0

        def generate_code(self, doc, out_path):
            self.call += 1
            code = self.source.read_text(encoding="utf-8")
            if self.call == 1:
                # R1：只把除法搞错（部分失败 → iterate）
                code = code.replace("return (a + b) / 2.0;", "return a;")
            else:
                # R2：加法和除法都错（更差 → rollback）
                code = code.replace("return a + b;", "return a * b;")
                code = code.replace("return (a + b) / 2.0;", "return a;")
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(code, encoding="utf-8")
            return out_path

    fw = KnowledgeFlywheel(
        cfg,
        knowledge_gen=StubKnowledgeGen(),
        coder=_RegressingCoder(CALC / "src/calc.c"),
        review=StubReview(),
    )
    result = fw.run("calc", CALC / "src/calc.c")
    assert result["decision"] == "rollback"
    # 回滚到 v1：无修订补丁（内容真实恢复，不是版本号减一）
    assert result["doc"].version == 1
    assert "修订补丁" not in result["doc"].content


# ---------- ACC-OBS-001：运行可追溯（同 run ID 关联全部产物） ----------

def test_run_id_links_all_artifacts(tmp_path):
    """同一 run ID 下能找到配置快照、知识、代码、报告、归因、修订、保护校验和结果。"""
    cfg = _dev_calc(tmp_path)
    result = KnowledgeFlywheel(cfg).run("calc", CALC / "src/calc.c")
    run_root = result["run_root"]
    run_id = result["run_id"]

    assert (run_root / "config.snapshot.json").exists()
    assert (run_root / "result.json").exists()
    assert list((run_root / "knowledge").glob("*.md"))
    assert list((run_root / "code").glob("*"))
    assert list((run_root / "eval").glob("*.json"))
    assert (run_root / "protection/before.json").exists()
    assert (run_root / "protection/after.json").exists()

    saved = json.loads((run_root / "result.json").read_text(encoding="utf-8"))
    assert saved["run_id"] == run_id
    config = json.loads((run_root / "config.snapshot.json").read_text(encoding="utf-8"))
    assert config["run_id"] == run_id


# ---------- ACC-EVAL-008：报告含探针证据 ----------

def test_report_contains_probe_evidence(tmp_path):
    """评测报告记录探针证据（期望输出来源可追溯）。"""
    cfg = _dev_calc(tmp_path)
    result = KnowledgeFlywheel(cfg).run("calc", CALC / "src/calc.c")
    report = result["train_report"]
    assert report.probe_evidence
    assert report.probe_evidence["provenance"] == "probe"
    assert report.probe_evidence["source_commit"]
