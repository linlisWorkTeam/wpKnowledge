"""契约 §6 错误码与验收场景专项测试（ACC-EVAL-* / ACC-SEC-* / ACC-FLOW-*）。"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fw.config import Config
from fw.error_codes import (COMPILE_FAILED, EMPTY_MODEL_OUTPUT, EVALSET_LEAK,
                            HOLDOUT_LEAK, INCOMPLETE_CONTEXT, INVALID_EVALUATION,
                            MAX_BUDGET, PROTECTION_MISMATCH, REGRESSION,
                            SOURCE_ACCESS_VIOLATION, UNSTABLE_RESULT, ZERO_CASES)
from fw.protection import ProtectionMismatch, snapshot, verify
from fw.sandbox import SandboxViolation, build_sandbox
from revise import decide
from roles import EvalReport

BASE = Path(__file__).resolve().parents[2]


def _cfg(**kw):
    values = dict(pass_threshold=0.8, variance_threshold=0.02,
                  repeat_eval=5, max_rounds=5)
    values.update(kw)
    return Config(**values).resolve(BASE)


# ---------- ACC-SEC-001：错误码 SOURCE_ACCESS_VIOLATION ----------

def test_sandbox_source_access_error_code(tmp_path):
    """Coder 触达源码区 → SOURCE_ACCESS_VIOLATION。"""
    cfg = Config(
        src_dir=tmp_path / "src-biz",
        interfaces_dir=tmp_path / "flywheel/interfaces",
        knowledge_dir=tmp_path / "flywheel/knowledge",
        work_dir=tmp_path / "flywheel/work",
    ).resolve(BASE)
    sandbox = build_sandbox(cfg)
    with pytest.raises(SandboxViolation) as exc_info:
        sandbox.assert_readable(tmp_path / "src-biz/secret.cpp")
    assert exc_info.value.error_code == SOURCE_ACCESS_VIOLATION


def test_sandbox_evalset_leak_error_code(tmp_path):
    """Coder 触达评测集/私有数据 → EVALSET_LEAK。"""
    cfg = Config(
        src_dir=tmp_path / "src-biz",
        interfaces_dir=tmp_path / "flywheel/interfaces",
        evalset_dir=tmp_path / "flywheel/eval-public",
        private_evalset_dir=tmp_path / "flywheel/eval-private",
        knowledge_dir=tmp_path / "flywheel/knowledge",
        work_dir=tmp_path / "flywheel/work",
    ).resolve(BASE)
    sandbox = build_sandbox(cfg)
    with pytest.raises(SandboxViolation) as exc_info:
        sandbox.assert_readable(tmp_path / "flywheel/eval-private/expected.json")
    assert exc_info.value.error_code in (SOURCE_ACCESS_VIOLATION, EVALSET_LEAK)


# ---------- ACC-SEC-004：PROTECTION_MISMATCH ----------

def test_protection_mismatch_error_code(tmp_path):
    """受保护文件被修改 → PROTECTION_MISMATCH。"""
    protected = tmp_path / "protected"
    protected.mkdir()
    file = protected / "knowledge.md"
    file.write_text("v1", encoding="utf-8")
    before = snapshot([protected])
    file.write_text("v2-tampered", encoding="utf-8")
    with pytest.raises(ProtectionMismatch) as exc_info:
        verify(before, [protected])
    assert exc_info.value.error_code == PROTECTION_MISMATCH


# ---------- ACC-EVAL-005：ZERO_CASES → stopped ----------

def test_zero_cases_stopped():
    """零用例 → stopped + ZERO_CASES + INVALID_EVALUATION。"""
    report = EvalReport(module="m", reason_codes=[ZERO_CASES])
    assert decide(report, None, _cfg()) == "stopped"
    assert INVALID_EVALUATION in report.reason_codes


# ---------- ACC-EVAL-001：编译失败 ----------

def test_compile_failed_iterate_then_stopped():
    """编译失败：有预算 → iterate；预算耗尽 → stopped。"""
    report = EvalReport(module="m", compile_ok=False, reason_codes=[COMPILE_FAILED])
    assert decide(report, None, _cfg(), budget_exhausted=False) == "iterate"
    assert decide(report, None, _cfg(), budget_exhausted=True) == "stopped"


# ---------- ACC-EVAL-004：unstable ----------

def _valid_report(**kw):
    """构造通过 valid 检查的评测报告（total>0 且 reps_count>0）。"""
    values = dict(module="m", compile_ok=True, total=10, passed=5,
                  reps_count=5, reps_mean=0.5, reps_variance=0.0, reps_min=0.5)
    values.update(kw)
    return EvalReport(**values)


def test_unstable_decision():
    """方差超限 → unstable（有预算时）。"""
    report = _valid_report(confidence=0.9, unstable=True,
                           reason_codes=[UNSTABLE_RESULT])
    assert decide(report, None, _cfg()) == "unstable"


# ---------- ACC-FLOW-001：MAX_BUDGET ----------

def test_max_budget_stopped():
    """预算耗尽且未达标 → stopped + MAX_BUDGET。"""
    report = _valid_report(confidence=0.5)
    assert decide(report, None, _cfg(), budget_exhausted=True) == "stopped"
    assert MAX_BUDGET in report.reason_codes


# ---------- ACC-EVAL-002：相似度不影响决策 ----------

def test_similarity_never_affects_decision():
    """相同测试结果不同相似度 → 相同 decision（相似度只诊断）。"""
    low = _valid_report(confidence=0.9, similarity=0.2)
    high = _valid_report(confidence=0.9, similarity=0.98)
    assert decide(low, None, _cfg()) == decide(high, None, _cfg()) == "pass"


# ---------- ACC-EVAL-003：不取最大值 ----------

def test_mean_not_max_in_gate():
    """gate 使用均值（0.6），不是最大单次值（1.0）。"""
    report = _valid_report(confidence=0.6, reps_mean=0.6, reps_min=0.4,
                           reps_variance=0.08)
    # 若误用最大值 1.0 会 pass；均值 0.6 低于 0.8 → iterate
    assert decide(report, None, _cfg()) == "iterate"


# ---------- 错误码常量完整性 ----------

def test_error_codes_are_stable_strings():
    """错误码是稳定字符串常量，跨组件一致。"""
    codes = [SOURCE_ACCESS_VIOLATION, HOLDOUT_LEAK, EMPTY_MODEL_OUTPUT,
             INCOMPLETE_CONTEXT, COMPILE_FAILED, ZERO_CASES, UNSTABLE_RESULT,
             REGRESSION, MAX_BUDGET, PROTECTION_MISMATCH, INVALID_EVALUATION]
    assert all(isinstance(code, str) and code.isupper() for code in codes)
    assert len(set(codes)) == len(codes)  # 无重复
