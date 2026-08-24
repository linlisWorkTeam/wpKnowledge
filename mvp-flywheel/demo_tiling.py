#!/usr/bin/env python3
"""端到端演示（tiling 模块）：用 cannbot add_custom 模板的真实 tiling 算法跑知识飞轮。

被测源码: samples/tiling/src/add_custom_tiling.cpp（纯 C++，来自算子平台模板）
评测集  : samples/tiling/evalset/test_tiling.cpp（原生测试文件，期望输出=探针真实结果）

用法:
  python3 demo_tiling.py                # 忠实 Coder，一轮通过
  python3 demo_tiling.py --bad-coder    # 缺陷 Coder，演示修订闭环
"""

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fw.config import Config
from fw.runner import KnowledgeFlywheel
from roles.stubs import StubCoder

BASE = Path(__file__).resolve().parent


def main():
    bad = "--bad-coder" in sys.argv
    # 产物持久化到固定目录（可随仓库提交，便于核查中间产物）
    work = BASE / "samples/tiling/run"
    if work.exists():
        shutil.rmtree(work)
    cfg = Config(
        src_dir=BASE / "samples/tiling/src",
        evalset_dir=BASE / "samples/tiling/evalset",
        work_dir=work / "data",
        knowledge_dir=work / "storage/knowledge",
        compiler="g++",
        compile_flags=["-Wall", "-Werror", "-std=c++11", "-I{src_dir}"],
    ).resolve(BASE)

    if bad:
        def broken(code: str) -> str:
            # 注入缺陷：去掉 tailNumLastCore 计算（模拟知识缺边界处理）
            return code.replace(
                "tiling.tailNumLastCore = totalLength - tiling.numPerCore * (blockNum - 1);", "")
        fw = KnowledgeFlywheel(cfg, coder=StubCoder(defect_fn=broken))
    else:
        fw = KnowledgeFlywheel(cfg)

    src_file = BASE / "samples/tiling/src/add_custom_tiling.cpp"
    result = fw.run("tiling", src_file)

    print("=" * 60)
    print("知识飞轮 MVP · tiling 模块端到端（算子平台真实算法）")
    print("=" * 60)
    print(f"被测源码 : samples/tiling/src/add_custom_tiling.cpp")
    print(f"评测集   : samples/tiling/evalset/test_tiling.cpp（探针真实输出）")
    if bad:
        print("Coder    : 注入缺陷（去掉 tailNumLastCore 计算）")
    else:
        print("Coder    : 忠实实现（正常）")
    print(f"最终决策 : {result['decision']}")
    print(f"迭代轮数 : {result['rounds']}")
    print()
    print("轮次历史 :")
    for h in result["history"]:
        print(f"  R{h['round']}: confidence={h['confidence']:.2f} "
              f"compile={h['compile_ok']} -> {h['decision']}")
    tr = result["train_report"]
    print()
    print(f"train 评测: passed={tr.passed}/{tr.total} confidence={tr.confidence:.2f} "
          f"similarity={tr.similarity:.2f}")
    print()
    print(f"知识文档 : {cfg.knowledge_dir / ('tiling_v%d.md' % result['doc'].version)}")
    print(f"生成代码 : {result['code_path']}")


if __name__ == "__main__":
    main()
