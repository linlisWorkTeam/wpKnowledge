#!/usr/bin/env python3
"""验证隔离布局：评测编译只依赖 interfaces_dir，不依赖 src_dir（源码在飞轮外）。

布局模拟：
  /tmp/flywheel-test/interfaces/   ← 只放接口头文件（评测 -I 指向）
  /tmp/src-biz-test/               ← 业务源码（飞轮外，评测不该碰）
"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from eval import detect_format, evaluate_native, find_native_tests
from fw.config import Config

BASE = Path(__file__).resolve().parent
SRC = BASE / "samples/tiling/src"

flywheel = Path("/tmp/flywheel-test")
src_biz = Path("/tmp/src-biz-test")
if flywheel.exists():
    shutil.rmtree(flywheel)
if src_biz.exists():
    shutil.rmtree(src_biz)

# 布局：src-biz（飞轮外，含 .h + .cpp 实现）；interfaces（飞轮内，只复制 .h）
src_biz.mkdir(parents=True)
flywheel.mkdir(parents=True)
interfaces = flywheel / "interfaces"
interfaces.mkdir()
for f in SRC.iterdir():
    shutil.copy2(f, src_biz / f.name)          # 源码全量进 src-biz
shutil.copy2(SRC / "add_custom_tiling.h", interfaces / "add_custom_tiling.h")  # 只复制头文件进 interfaces

cfg = Config(
    src_dir=src_biz,                            # 飞轮外源码（知识生成读这里）
    interfaces_dir=interfaces,                  # 飞轮内接口头文件（评测 -I 这里）
    evalset_dir=BASE / "samples/tiling/evalset",
    work_dir=flywheel / "data",
    knowledge_dir=flywheel / "knowledge",
    compiler="g++",
    compile_flags=["-Wall", "-Werror", "-std=c++11", "-I{interfaces_dir}"],
).resolve(BASE)

# 模拟 Coder 生成的代码 = src_biz 里的实现副本（仅作评测输入，正常流程是生成代码）
code_path = flywheel / "gen_tiling.cpp"
shutil.copy2(src_biz / "add_custom_tiling.cpp", code_path)

fmt = detect_format(cfg.evalset_dir, cfg)
print(f"评测集格式: {fmt}")
test_files = find_native_tests(cfg.evalset_dir, cfg, "tiling")
print(f"测试文件: {[t.name for t in test_files]}")
report = evaluate_native("tiling", code_path, test_files, cfg, src_text="", work_dir=cfg.work_dir)
print(f"编译通过: {report.compile_ok}  通过: {report.passed}/{report.total}  confidence={report.confidence:.2f}")
print(f"编译命令用的头文件目录: {cfg.eval_include_dir()}")
assert report.compile_ok and report.passed == report.total == 8, "隔离布局评测失败"
print("✅ 隔离布局验证通过：评测编译只用 interfaces/，不依赖 src-biz/")
