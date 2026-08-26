"""新门禁（2026-08-26 收敛）专项测试：均值±方差 / UNSTABLE / 禁取最好成绩。"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eval import _apply_reps, _summarize_reps
from fw.config import Config
from revise import decide
from roles import EvalReport

BASE = Path(__file__).resolve().parents[1]


def _cfg(**kw):
    base = dict(pass_threshold=0.8, max_rounds=5, repeat_eval=5,
                variance_threshold=0.02)
    base.update(kw)
    return Config(**base)


# ---------- _summarize_reps / _apply_reps ----------

def test_summarize_stable():
    """全过（每次 1.0）→ 方差 0，不 unstable。"""
    s = _summarize_reps([1.0, 1.0, 1.0, 1.0, 1.0], _cfg())
    assert s["mean"] == pytest.approx(1.0)
    assert s["variance"] == pytest.approx(0.0)
    assert s["unstable"] is False


def test_summarize_fluctuating():
    """忽过忽不过 → 方差大，UNSTABLE。"""
    s = _summarize_reps([1.0, 0.0, 1.0, 0.0, 1.0], _cfg())
    assert s["mean"] == pytest.approx(0.6)
    assert s["variance"] > 0.02
    assert s["unstable"] is True


def test_summarize_min():
    """最差值被记录。"""
    s = _summarize_reps([1.0, 0.875, 1.0, 1.0, 0.875], _cfg())
    assert s["min"] == pytest.approx(0.875)


def test_apply_reps_writes_report():
    """_apply_reps 把统计写入 EvalReport 且 confidence=均值（非最大）。"""
    rep = EvalReport(module="m", passed=8, total=8)
    _apply_reps(rep, [1.0, 0.75, 1.0, 0.75, 1.0], _cfg())
    assert rep.confidence == pytest.approx(0.9)   # 均值，不是 1.0
    assert rep.reps_count == 5
    assert rep.reps_min == pytest.approx(0.75)
    assert rep.unstable is False


# ---------- decide：UNSTABLE 分支 ----------

def test_decide_unstable_not_pass():
    """方差大 → 即使均值 ≥ 门限也不判 pass，判 unstable。"""
    rep = EvalReport(module="m", compile_ok=True, confidence=0.9,
                     unstable=True)
    assert decide(rep, None, _cfg()) == "unstable"


def test_decide_unstable_low_conf_iterate():
    """方差大 + 均值低 → unstable（仍进迭代而非 pass）。"""
    rep = EvalReport(module="m", compile_ok=True, confidence=0.4,
                     unstable=True)
    assert decide(rep, None, _cfg()) == "unstable"


def test_decide_pass_when_stable():
    """稳定且均值 ≥ 门限 → pass。"""
    rep = EvalReport(module="m", compile_ok=True, confidence=0.9,
                     unstable=False)
    assert decide(rep, None, _cfg()) == "pass"


def test_decide_iterate_when_unstable_false_low():
    """稳定但均值低 → iterate（且不低于上轮）。"""
    rep = EvalReport(module="m", compile_ok=True, confidence=0.5,
                     unstable=False)
    assert decide(rep, None, _cfg()) == "iterate"


def test_decide_rollback_on_regression():
    """稳定但低于上轮 → rollback。"""
    rep = EvalReport(module="m", compile_ok=True, confidence=0.5,
                     unstable=False)
    assert decide(rep, 0.7, _cfg()) == "rollback"


def test_decide_compile_fail_unstable_ignored():
    """编译失败时即使 unstable 标记也按失败走（compile_ok=False 优先）。"""
    rep = EvalReport(module="m", compile_ok=False, confidence=0.0,
                     unstable=True)
    # 编译失败不进测试：confidence 0 < 门限，prev None → iterate（与旧语义一致）
    assert decide(rep, None, _cfg()) == "iterate"
