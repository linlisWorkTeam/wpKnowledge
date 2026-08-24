"""评测闭环单测。"""
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eval import compile_check, evaluate, load_cases, similarity
from eval.holdout import is_holdout, split_cases
from fw.config import Config

BASE = Path(__file__).resolve().parents[1]


@pytest.fixture()
def cfg(tmp_path):
    c = Config(
        src_dir=BASE / "samples/src",
        evalset_dir=BASE / "samples/evalset",
        work_dir=tmp_path / "data",
        knowledge_dir=tmp_path / "storage/knowledge",
    ).resolve(BASE)
    return c


def test_compile_check_ok(cfg):
    ok, errors = compile_check(BASE / "samples/src/calc.c", cfg)
    assert ok is True
    assert errors == []


def test_compile_check_fail(cfg, tmp_path):
    bad = tmp_path / "bad.c"
    bad.write_text("int broken( { return 1; }")
    ok, errors = compile_check(bad, cfg)
    assert ok is False
    assert len(errors) > 0


def test_similarity_basic():
    assert similarity("int a;", "int a;") == pytest.approx(1.0)
    assert similarity("int a;", "int b;") < 1.0
    assert similarity("", "x") == 0.0


def test_load_cases(cfg):
    cases = load_cases(cfg.evalset_dir)
    assert len(cases) == 9
    assert all("function" in c for c in cases)


def test_split_cases_explicit(cfg):
    cases = load_cases(cfg.evalset_dir)
    splits = split_cases(cases, 0.2)
    assert len(splits["holdout"]) == 2  # max3 两条显式 holdout
    assert len(splits["train"]) == 7


def test_is_holdout_hash_based(cfg):
    # 未显式标注 split 的按模块哈希
    assert is_holdout({"module": "calc", "function": "x"}, 0.0) is False
    # 显式标注优先
    assert is_holdout({"module": "calc", "split": "holdout"}, 0.0) is True


def test_evaluate_full_pass(cfg):
    """真实源码作为被测代码 → 全部通过。"""
    cases = [c for c in load_cases(cfg.evalset_dir) if c.get("split") != "holdout"]
    report = evaluate("calc", BASE / "samples/src/calc.c", cases, cfg,
                      src_text=(BASE / "samples/src/calc.c").read_text())
    assert report.compile_ok is True
    assert report.passed == report.total
    assert report.confidence == pytest.approx(1.0)
    assert report.similarity == pytest.approx(1.0)


def test_evaluate_wrong_code_fails(cfg, tmp_path):
    """错误实现 → 测试失败，置信度降低。"""
    wrong = tmp_path / "wrong.c"
    wrong.write_text("""
#include "calc.h"
int add(int a, int b) { return a * b; }   /* 故意写错 */
int clamp(int x, int lo, int hi) { return x; }
int max3(int a, int b, int c) { return a; }
double mean(double a, double b) { return a; }
""")
    cases = [c for c in load_cases(cfg.evalset_dir) if c.get("split") != "holdout"]
    report = evaluate("calc", wrong, cases, cfg, src_text="")
    assert report.compile_ok is True
    assert report.passed < report.total
    assert report.confidence < 1.0
