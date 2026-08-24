"""tiling 模块端到端测试（算子平台真实算法：cannbot add_custom 模板）。"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eval import detect_format, evaluate_native, find_native_tests
from fw.config import Config
from fw.runner import KnowledgeFlywheel
from roles.stubs import StubCoder

BASE = Path(__file__).resolve().parents[1]
TILING = BASE / "samples/tiling"


@pytest.fixture()
def tiling_cfg(tmp_path):
    return Config(
        src_dir=TILING / "src",
        evalset_dir=TILING / "evalset",
        work_dir=tmp_path / "data",
        knowledge_dir=tmp_path / "storage/knowledge",
        compiler="g++",
        compile_flags=["-Wall", "-Werror", "-std=c++11", "-I{src_dir}"],
    ).resolve(BASE)


def test_tiling_detect_native(tiling_cfg):
    """tiling 评测集是原生 C++ 测试文件。"""
    assert detect_format(TILING / "evalset", tiling_cfg) == "native"


def test_tiling_evaluate_src_pass(tiling_cfg, tmp_path):
    """真实源码 → 8/8 全过（探针验证过的期望输出）。"""
    files = find_native_tests(TILING / "evalset", tiling_cfg, "tiling")
    assert len(files) == 1
    report = evaluate_native("tiling", TILING / "src/add_custom_tiling.cpp", files,
                             tiling_cfg, work_dir=tmp_path)
    assert report.compile_ok is True
    assert report.passed == 8
    assert report.total == 8
    assert report.confidence == pytest.approx(1.0)


def test_tiling_evaluate_wrong_code(tiling_cfg, tmp_path):
    """缺 tailNumLastCore 的实现 → 全部失败。"""
    wrong = tmp_path / "wrong.cpp"
    wrong.write_text("""
#include "add_custom_tiling.h"
AddTilingData compute_tiling(uint32_t totalLength, uint32_t availableCoreNum)
{
    AddTilingData tiling;
    tiling.totalLength = totalLength;
    uint32_t cores = (availableCoreNum == 0) ? 1 : availableCoreNum;
    uint32_t totalTiles = (totalLength + TILE_LENGTH - 1) / TILE_LENGTH;
    uint32_t tilesPerCore = (totalTiles + cores - 1) / cores;
    uint32_t blockNum = (totalTiles + tilesPerCore - 1) / tilesPerCore;
    tiling.blockNum = blockNum;
    tiling.numPerCore = tilesPerCore * TILE_LENGTH;
    /* 缺 tailNumLastCore 赋值 */
    return tiling;
}
""")
    files = find_native_tests(TILING / "evalset", tiling_cfg, "tiling")
    report = evaluate_native("tiling", wrong, files, tiling_cfg, work_dir=tmp_path)
    assert report.compile_ok is True
    assert report.passed == 0
    assert report.confidence == 0.0


def test_tiling_flywheel_pass(tiling_cfg):
    """完整飞轮：真实 tiling 算法 → 一轮通过。"""
    fw = KnowledgeFlywheel(tiling_cfg)
    result = fw.run("tiling", TILING / "src/add_custom_tiling.cpp")
    assert result["decision"] == "pass"
    assert result["rounds"] == 1
    assert result["train_report"].passed == 8


def test_tiling_flywheel_revise_loop(tiling_cfg):
    """完整飞轮：缺陷 Coder → R1 失败 → 修订 → R2 通过。"""
    def broken(code: str) -> str:
        return code.replace(
            "tiling.tailNumLastCore = totalLength - tiling.numPerCore * (blockNum - 1);", "")

    fw = KnowledgeFlywheel(tiling_cfg, coder=StubCoder(defect_fn=broken))
    result = fw.run("tiling", TILING / "src/add_custom_tiling.cpp")
    assert result["decision"] == "pass"
    assert result["rounds"] == 2
    assert result["history"][0]["decision"] == "iterate"
    assert result["history"][0]["confidence"] == pytest.approx(0.0)
    assert result["history"][1]["decision"] == "pass"
