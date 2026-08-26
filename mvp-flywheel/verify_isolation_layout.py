#!/usr/bin/env python3
"""跨平台验证评测编译只依赖 interfaces_dir，不依赖源码目录。"""

import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from eval import evaluate_native, find_native_tests
from fw.config import Config

BASE = Path(__file__).resolve().parent


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="flywheel-layout-") as temp:
        root = Path(temp)
        flywheel = root / "flywheel"
        src_biz = root / "src-biz"
        interfaces = flywheel / "interfaces"
        work = flywheel / "work"
        knowledge = flywheel / "knowledge"
        for directory in (src_biz, interfaces, work, knowledge):
            directory.mkdir(parents=True)

        sample_src = BASE / "samples/tiling/src"
        shutil.copy2(sample_src / "add_custom_tiling.cpp", src_biz / "add_custom_tiling.cpp")
        shutil.copy2(sample_src / "add_custom_tiling.h", src_biz / "add_custom_tiling.h")
        shutil.copy2(BASE / "samples/tiling/interfaces/add_custom_tiling.h",
                     interfaces / "add_custom_tiling.h")

        generated = flywheel / "generated.cpp"
        shutil.copy2(src_biz / "add_custom_tiling.cpp", generated)
        cfg = Config(
            src_dir=src_biz,
            interfaces_dir=interfaces,
            evalset_dir=BASE / "samples/tiling/evalset",
            work_dir=work,
            knowledge_dir=knowledge,
            compiler="g++",
            compile_flags=["-Wall", "-Werror", "-std=c++11", "-I{interfaces_dir}"],
            repeat_eval=1,
        ).resolve(BASE)
        tests = find_native_tests(cfg.evalset_dir, cfg, "tiling")
        report = evaluate_native("tiling", generated, tests, cfg, work_dir=work)
        assert report.compile_ok and report.passed == report.total == 8
        assert cfg.eval_include_dir() == interfaces.resolve()

    print("PASS: 评测仅使用 interfaces/，无需从 src-biz 读取头文件")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
