#!/usr/bin/env python3
"""验证沙箱隔离（问题1）：Coder 进程在 src-biz 布局下无法读取源码。

布局模拟（对应《codeagent执行手册》§0.1）：
  /tmp/flywheel-test/            ← Coder 工作区（白名单）
    interfaces/                  ← 接口头文件副本（Coder 可读）
    knowledge/                   ← 知识文档（Coder 可读）
    data/                        ← 运行时产物
  /tmp/src-biz-test/             ← 业务源码（飞轮外，Coder 禁止读取）

验证点：
1. Coder 可读：知识文档、接口头文件
2. Coder 禁止读：src-biz 源码实现（抛 SandboxViolation）
3. 路径穿越（../src-biz/...）被 resolve 拦截
4. LLMCoder 沙箱：输出路径只能在白名单内
"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fw.config import Config
from fw.sandbox import SandboxViolation, build_sandbox
from roles.llm_roles import LLMCoder

BASE = Path(__file__).resolve().parent
SRC = BASE / "samples/tiling/src"

flywheel = Path("/tmp/flywheel-test")
src_biz = Path("/tmp/src-biz-test")
for d in (flywheel, src_biz):
    if d.exists():
        shutil.rmtree(d)

# 布局：src-biz（飞轮外，含 .h + .cpp 实现）；interfaces（飞轮内，只复制 .h）
src_biz.mkdir(parents=True)
flywheel.mkdir(parents=True)
interfaces = flywheel / "interfaces"
knowledge = flywheel / "knowledge"
data = flywheel / "data"
for d in (interfaces, knowledge, data):
    d.mkdir()
for f in SRC.iterdir():
    shutil.copy2(f, src_biz / f.name)          # 源码全量进 src-biz
shutil.copy2(SRC / "add_custom_tiling.h", interfaces / "add_custom_tiling.h")  # 只复制头文件

cfg = Config(
    src_dir=src_biz,
    interfaces_dir=interfaces,
    evalset_dir=BASE / "samples/tiling/evalset",
    work_dir=data,
    knowledge_dir=knowledge,
    compiler="g++",
    compile_flags=["-Wall", "-Werror", "-std=c++11", "-I{interfaces_dir}"],
).resolve(BASE)

sb = build_sandbox(cfg)
print(f"沙箱白名单: {sb.allowed_dirs()}")

# 1. 可读：知识 + 接口
kb = knowledge / "tiling_v1.md"
kb.write_text("# tiling 知识")
assert sb.read_text(kb) == "# tiling 知识"
assert sb.read_text(interfaces / "add_custom_tiling.h").startswith("#ifndef")
print("✅ Coder 可读：知识文档、接口头文件")

# 2. 禁止读：源码实现
try:
    sb.assert_readable(src_biz / "add_custom_tiling.cpp")
    print("❌ 沙箱放行了源码实现！")
    sys.exit(1)
except SandboxViolation as e:
    print(f"✅ 沙箱拦截源码实现: {e}")

# 3. 路径穿越被拦
try:
    sb.assert_readable(data / "../src-biz/add_custom_tiling.cpp")
    print("❌ 路径穿越未被拦截！")
    sys.exit(1)
except SandboxViolation:
    print("✅ 沙箱拦截路径穿越（../src-biz/...）")

# 4. LLMCoder 输出路径必须白名单内（非法输出路径被拦）
coder = LLMCoder(cfg=cfg)
try:
    coder.generate_code.__self__  # 触达实例
    from roles import KnowledgeDoc
    doc = KnowledgeDoc(module="tiling", content="# tiling")
    coder.generate_code(doc, src_biz / "evil.cpp")
    print("❌ Coder 把代码写进了 src-biz（沙箱失效）！")
    sys.exit(1)
except SandboxViolation as e:
    print(f"✅ Coder 输出路径被沙箱拦截: {e}")

print("\n✅ 沙箱隔离验证全部通过：源码在飞轮外，Coder 物理摸不到")
