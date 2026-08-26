"""SDD P0 规格级验收测试。"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fw.config import Config, ConfigError
from fw.protection import ProtectionMismatch, snapshot, verify
from fw.runner import KnowledgeFlywheel, KnowledgeLeakError, assert_no_source_leak
from fw.sandbox import SandboxViolation, build_sandbox
from revise import CorrectionQueue, apply_revision, decide
from roles import Attribution, Correction, CoderAgent, EvalReport, KnowledgeDoc
from roles.providers import CodeAgentProvider
from roles.stubs import StubKnowledgeGen, StubReview

BASE = Path(__file__).resolve().parents[2]
CALC = BASE / "tests/fixtures/calc"


def _prod_config(tmp_path, **changes):
    values = dict(
        mode="production",
        src_dir=tmp_path / "src-biz",
        interfaces_dir=tmp_path / "flywheel/interfaces",
        evalset_dir=tmp_path / "flywheel/eval-public",
        private_evalset_dir=tmp_path / "flywheel/eval-private",
        work_dir=tmp_path / "flywheel/artifacts",
        knowledge_dir=tmp_path / "flywheel/knowledge",
        ledger_path=tmp_path / "flywheel/ledger.json",
        require_holdout=True,
        repeat_generation=5,
        repeat_eval=1,
        model_provider="codeagent",
        model_id="GLM-5.1",
        source_commit="a" * 40,
    )
    values.update(changes)
    return Config(**values).resolve(tmp_path)


def _dev_calc(tmp_path, native=False, require_holdout=False):
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


def test_production_config_accepts_only_explicit_safe_baseline(tmp_path):
    cfg = _prod_config(tmp_path)
    assert cfg.validate() is cfg
    assert cfg.eval_include_dir() == (tmp_path / "flywheel/interfaces").resolve()


@pytest.mark.parametrize("changes", [
    {"interfaces_dir": None},
    {"require_holdout": False},
    {"repeat_generation": 1},
    {"model_provider": "deepseek"},
    {"model_id": "other"},
    {"source_commit": ""},
])
def test_production_config_fails_closed(tmp_path, changes):
    with pytest.raises(ConfigError):
        _prod_config(tmp_path, **changes).validate()


def test_deepseek_requires_explicit_experimental_mode(tmp_path):
    cfg = Config(model_provider="deepseek", mode="development").resolve(tmp_path)
    with pytest.raises(ConfigError):
        cfg.validate()


def test_gate_threshold_is_configurable_and_zero_cases_stop(tmp_path):
    report = EvalReport(module="m", compile_ok=True, total=10, passed=9,
                        confidence=0.9, reps_count=5)
    assert report.passes(0.8) is True
    assert report.passes(0.95) is False
    zero = EvalReport(module="m", compile_ok=True, reason_codes=["ZERO_CASES"])
    assert decide(zero, None, Config().resolve(tmp_path)) == "stopped"


def test_holdout_public_report_redacts_details():
    report = EvalReport(
        module="m", split="holdout", compile_ok=True, total=1, passed=0,
        confidence=0.0, reps_count=1,
        failures=["secret expected=42"],
        repetitions=[{"input": "secret"}],
        generation_results=[{"failure": "secret"}],
    )
    public = report.public_copy()
    assert public.failures == []
    assert public.repetitions == []
    assert public.generation_results == []


def test_native_without_holdout_cannot_publish_when_required(tmp_path):
    cfg = _dev_calc(tmp_path, native=True, require_holdout=True)
    result = KnowledgeFlywheel(cfg).run("calc", CALC / "src/calc.c")
    assert result["decision"] == "stopped"
    assert result["doc"].status == "draft"
    assert list(cfg.knowledge_dir.glob("*.md")) == []


def test_json_holdout_must_pass_before_publish(tmp_path):
    cfg = _dev_calc(tmp_path, require_holdout=True)
    result = KnowledgeFlywheel(cfg).run("calc", CALC / "src/calc.c")
    assert result["decision"] == "pass"
    assert result["holdout_report"] is not None
    assert result["doc"].status == "verified"
    assert len(list(cfg.knowledge_dir.glob("calc_v*.md"))) == 1


def test_sandbox_separates_read_and_write_and_denies_source(tmp_path):
    cfg = Config(
        src_dir=tmp_path / "src-biz",
        interfaces_dir=tmp_path / "flywheel/interfaces",
        evalset_dir=tmp_path / "flywheel/eval",
        knowledge_dir=tmp_path / "flywheel/knowledge",
        work_dir=tmp_path / "flywheel/work",
    ).resolve(BASE)
    sandbox = build_sandbox(cfg)
    with pytest.raises(SandboxViolation):
        sandbox.assert_readable(cfg.work_dir / "old-report.json")
    assert sandbox.assert_writable(cfg.work_dir / "round/code.cpp")
    with pytest.raises(SandboxViolation):
        sandbox.assert_readable(cfg.src_dir / "secret.cpp")


def test_full_sha256_protection_detects_changes(tmp_path):
    protected = tmp_path / "protected"
    protected.mkdir()
    file = protected / "source.cpp"
    file.write_text("before", encoding="utf-8")
    before = snapshot([protected])
    assert len(next(iter(before.values()))) == 64
    verify(before, [protected])
    file.write_text("after", encoding="utf-8")
    with pytest.raises(ProtectionMismatch):
        verify(before, [protected])


def test_revision_is_immutable_and_ledger_history_survives_clear(tmp_path):
    cfg = Config(ledger_path=tmp_path / "ledger.json").resolve(BASE)
    original = KnowledgeDoc(module="m", version=1, content="v1")

    def mutating_revision(doc, corrections):
        doc.content = "v2"
        return doc

    revised = apply_revision(original, [Correction("c1", "m#x", "passes")], mutating_revision)
    assert original.content == "v1"
    assert revised.content == "v2"
    assert revised.version == 2 and revised.parent_version == 1

    queue = CorrectionQueue(cfg, run_id="run-1")
    queue.clear()
    queue.push(Attribution(module="m", corrections=[Correction("c1", "m#x", "passes")]))
    queue.clear()
    reloaded = CorrectionQueue(cfg, run_id="run-1")
    assert reloaded.pop_pending() == []
    assert any(item["id"] == "c1" for item in reloaded.history)


def test_source_leak_detector_rejects_implementation_line():
    source = "int calculate(int input) {\n    return input * 1024 + 123456789;\n}\n"
    knowledge = "算法说明：\n    return input * 1024 + 123456789;"
    with pytest.raises(KnowledgeLeakError):
        assert_no_source_leak(knowledge, source)


def test_codeagent_provider_uses_json_contract(tmp_path):
    helper = tmp_path / "fake_codeagent.py"
    helper.write_text(
        "import json, sys\n"
        "payload=json.loads(sys.stdin.read())\n"
        "print(json.dumps({'content': payload['model'] + ':ok'}))\n",
        encoding="utf-8",
    )
    provider = CodeAgentProvider([sys.executable, str(helper)], "GLM-5.1")
    assert provider.chat([{"role": "user", "content": "x"}], 0.1, 10, 10) == "GLM-5.1:ok"


class _SequenceCoder(CoderAgent):
    def __init__(self, source: Path):
        self.source = source
        self.calls = 0

    def generate_code(self, doc: KnowledgeDoc, out_path: Path) -> Path:
        self.calls += 1
        code = self.source.read_text(encoding="utf-8")
        if self.calls == 1:
            code = code.replace("return a + b;", "return a * b;")
            code = code.replace("return (a + b) / 2.0;", "return a;")
        else:
            code = code.replace("return a + b;", "return a * b;")
            code = code.replace("return x;", "return 0;")
            code = code.replace("return m;", "return 0;")
            code = code.replace("return (a + b) / 2.0;", "return 0;")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(code, encoding="utf-8")
        return out_path


def test_regression_rolls_back_real_content_not_only_version(tmp_path):
    cfg = _dev_calc(tmp_path)
    cfg.max_rounds = 3
    fw = KnowledgeFlywheel(
        cfg,
        knowledge_gen=StubKnowledgeGen(),
        coder=_SequenceCoder(CALC / "src/calc.c"),
        review=StubReview(),
    )
    result = fw.run("calc", CALC / "src/calc.c")
    assert result["decision"] == "rollback"
    assert result["doc"].version == 1
    assert "修订补丁" not in result["doc"].content


def test_run_artifacts_share_run_id(tmp_path):
    cfg = _dev_calc(tmp_path, require_holdout=True)
    result = KnowledgeFlywheel(cfg).run("calc", CALC / "src/calc.c")
    run_root = result["run_root"]
    assert (run_root / "config.snapshot.json").exists()
    assert (run_root / "result.json").exists()
    saved = json.loads((run_root / "result.json").read_text(encoding="utf-8"))
    assert saved["run_id"] == result["run_id"]
    assert list((run_root / "code").glob("*"))
    assert list((run_root / "eval").glob("*.json"))
