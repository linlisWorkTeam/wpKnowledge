"""评测集兼容口测试：JSON 模式 + 原生测试文件模式（用户本地测试集）。"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eval import detect_format, evaluate_native, find_native_tests, load_cases
from fw.config import Config
from fw.runner import KnowledgeFlywheel
from roles.stubs import StubCoder

BASE = Path(__file__).resolve().parents[1]


@pytest.fixture()
def cfg(tmp_path):
    return Config(
        src_dir=BASE / "tests/fixtures/calc/src",
        evalset_dir=BASE / "tests/fixtures/calc/evalset",
        work_dir=tmp_path / "data",
        knowledge_dir=tmp_path / "storage/knowledge",
    ).resolve(BASE)


def test_detect_json(cfg):
    """tests/fixtures/calc/evalset 有 cases/*.json → json 模式。"""
    assert detect_format(BASE / "tests/fixtures/calc/evalset", cfg) == "json"


def test_detect_native(cfg):
    """tests/fixtures/calc/evalset_native 有 test_*.c → native 模式。"""
    assert detect_format(BASE / "tests/fixtures/calc/evalset_native", cfg) == "native"


def test_detect_forced_native(cfg):
    """显式 evalset_format=native 时即使有 json 也按 native。"""
    cfg.evalset_format = "native"
    assert detect_format(BASE / "tests/fixtures/calc/evalset", cfg) == "native"


def test_find_native_tests(cfg):
    files = find_native_tests(BASE / "tests/fixtures/calc/evalset_native", cfg, "calc")
    assert len(files) == 1
    assert files[0].name == "test_calc.c"


def test_evaluate_native_pass(cfg, tmp_path):
    """原生测试文件 + 真实源码 → 全过。"""
    files = find_native_tests(BASE / "tests/fixtures/calc/evalset_native", cfg, "calc")
    report = evaluate_native("calc", BASE / "tests/fixtures/calc/src/calc.c", files, cfg,
                             src_text=(BASE / "tests/fixtures/calc/src/calc.c").read_text(),
                             work_dir=tmp_path)
    assert report.compile_ok is True
    assert report.passed == report.total
    assert report.total == 9  # 9 用例；重复评测取最大通过数，total 以单次为准
    assert report.confidence == pytest.approx(1.0)


def test_evaluate_native_wrong_code(cfg, tmp_path):
    """原生测试文件 + 错误实现 → 失败。"""
    wrong = tmp_path / "wrong.c"
    wrong.write_text("""
#include "calc.h"
int add(int a, int b) { return a * b; }
int clamp(int x, int lo, int hi) { return x; }
int max3(int a, int b, int c) { return a; }
double mean(double a, double b) { return a; }
""")
    files = find_native_tests(BASE / "tests/fixtures/calc/evalset_native", cfg, "calc")
    report = evaluate_native("calc", wrong, files, cfg, work_dir=tmp_path)
    assert report.compile_ok is True
    assert report.passed < report.total
    assert report.confidence < 1.0


def test_flywheel_native_end_to_end(cfg, tmp_path):
    """native 评测集跑完整飞轮（配置覆盖 evalset_dir）。"""
    cfg.evalset_dir = BASE / "tests/fixtures/calc/evalset_native"
    cfg.work_dir = tmp_path / "data"
    cfg.knowledge_dir = tmp_path / "storage/knowledge"
    fw = KnowledgeFlywheel(cfg)
    result = fw.run("calc", BASE / "tests/fixtures/calc/src/calc.c")
    assert result["decision"] == "pass"
    assert result["train_report"].confidence == pytest.approx(1.0)
    # native 模式无 holdout
    assert result["holdout_report"] is None


def test_flywheel_native_iterates(cfg, tmp_path):
    """native 评测集 + 缺陷 Coder → 修订闭环生效。"""
    cfg.evalset_dir = BASE / "tests/fixtures/calc/evalset_native"
    cfg.work_dir = tmp_path / "data"
    cfg.knowledge_dir = tmp_path / "storage/knowledge"

    def broken(code: str) -> str:
        return code.replace("return a + b;", "return a * b;")

    fw = KnowledgeFlywheel(cfg, coder=StubCoder(defect_fn=broken))
    result = fw.run("calc", BASE / "tests/fixtures/calc/src/calc.c")
    assert result["decision"] == "pass"
    assert result["rounds"] == 2
    assert result["history"][0]["decision"] == "iterate"
    assert result["history"][1]["decision"] == "pass"
