"""修订闭环 + 编排层单测。"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eval.holdout import split_cases
from eval import load_cases
from fw.config import Config
from fw.runner import KnowledgeFlywheel
from revise import CorrectionQueue, decide
from roles import Correction, EvalReport, KnowledgeDoc
from roles.stubs import StubCoder, StubKnowledgeGen, StubReview

BASE = Path(__file__).resolve().parents[1]


@pytest.fixture()
def cfg(tmp_path):
    return Config(
        src_dir=BASE / "tests/fixtures/calc/src",
        evalset_dir=BASE / "tests/fixtures/calc/evalset",
        work_dir=tmp_path / "data",
        knowledge_dir=tmp_path / "storage/knowledge",
    ).resolve(BASE)


def test_correction_queue_roundtrip(cfg):
    q = CorrectionQueue(cfg)
    q.clear()
    from roles import Attribution
    a = Attribution(module="calc", corrections=[
        Correction(id="calc-1", knowledge_path="calc 函数", criterion="测试通过",
                   detail="失败 2 条"),
    ])
    q.push(a)
    pending = q.pop_pending()
    assert len(pending) == 1
    assert pending[0].id == "calc-1"
    assert pending[0].criterion == "测试通过"
    q.mark_done("calc-1", ok=True)
    assert q.pop_pending() == []
    q.clear()


def test_decide_pass_iterate_rollback(cfg):
    r_pass = EvalReport(module="calc", compile_ok=True, passed=9, total=9,
                        confidence=1.0, reps_count=5)
    assert decide(r_pass, prev_confidence=0.5, cfg=cfg) == "pass"

    r_mid = EvalReport(module="calc", compile_ok=True, passed=6, total=9,
                       confidence=0.67, reps_count=5)
    assert decide(r_mid, prev_confidence=0.5, cfg=cfg) == "iterate"

    r_down = EvalReport(module="calc", compile_ok=True, passed=4, total=9,
                        confidence=0.44, reps_count=5)
    assert decide(r_down, prev_confidence=0.67, cfg=cfg) == "rollback"


def test_decide_compile_fail_not_pass(cfg):
    r = EvalReport(module="calc", compile_ok=False, passed=0, total=9,
                   confidence=0.0)
    assert decide(r, prev_confidence=None, cfg=cfg) == "iterate"


def test_flywheel_end_to_end_pass(cfg):
    """真实源码作为知识来源 + 忠实 Coder → 一轮通过。"""
    fw = KnowledgeFlywheel(cfg)
    result = fw.run("calc", BASE / "tests/fixtures/calc/src/calc.c")
    assert result["decision"] == "pass"
    assert result["rounds"] == 1
    assert result["train_report"].confidence == pytest.approx(1.0)
    # 知识文档已写入
    assert cfg.knowledge_dir.exists()
    assert len(list(cfg.knowledge_dir.glob("calc_v*.md"))) >= 1


def test_flywheel_iterates_on_bad_coder(cfg):
    """Coder 生成错误代码 → 评测失败 → 迭代修订 → 最终通过。"""
    def broken(code: str) -> str:
        # 注入缺陷：把 add 改成乘法，clamp 去掉边界
        return code.replace("return a + b;", "return a * b;")\
                   .replace("if (x < lo) return lo;\n    if (x > hi) return hi;", "")

    fw = KnowledgeFlywheel(cfg, coder=StubCoder(defect_fn=broken))
    result = fw.run("calc", BASE / "tests/fixtures/calc/src/calc.c")
    # R1 有缺陷失败 → 修订 → R2 知识含补丁 → Coder 修正 → 通过
    assert result["decision"] == "pass"
    assert result["rounds"] == 2
    assert result["history"][0]["decision"] == "iterate"
    assert result["history"][1]["decision"] == "pass"
    assert result["train_report"].confidence == pytest.approx(1.0)


def test_flywheel_holdout_reported(cfg):
    """holdout 用例参与评测但只报告，不进入修订反馈。"""
    cases = load_cases(cfg.evalset_dir)
    splits = split_cases(cases, 0.2)
    assert len(splits["holdout"]) == 2

    fw = KnowledgeFlywheel(cfg)
    result = fw.run("calc", BASE / "tests/fixtures/calc/src/calc.c")
    assert result["holdout_report"] is not None
    assert result["holdout_report"].module == "calc"
    # 真实源码 → holdout 也全过
    assert result["holdout_report"].confidence == pytest.approx(1.0)
