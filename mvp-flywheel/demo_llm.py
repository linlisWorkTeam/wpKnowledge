#!/usr/bin/env python3
"""真 LLM 端到端（tiling 模块）：知识生成保留桩，Coder/Review 走真实 DeepSeek。

对比 demo_tiling.py（全桩）：
- 知识生成 : StubKnowledgeGen（用户指定保留桩：从源码提取函数）
- Coder    : LLMCoder（DeepSeek 真写代码，只看知识+接口头文件，不读源码实现）
- Review   : LLMReview（DeepSeek 真归因，看失败用例详情）

用法:
  python3 demo_llm.py                # 忠实模式：知识生成桩 + LLM Coder + LLM Review
"""

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fw.config import Config
from fw.runner import KnowledgeFlywheel
from roles.llm_roles import LLMCoder, LLMReview
from roles.stubs import StubKnowledgeGen

BASE = Path(__file__).resolve().parent


def main():
    # 产物持久化到固定目录（与桩跑的 run/ 分开，便于对比）
    work = BASE / "samples/tiling/run_llm"
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

    fw = KnowledgeFlywheel(
        cfg,
        knowledge_gen=StubKnowledgeGen(),   # 保留桩
        coder=LLMCoder(),                   # 真 LLM 写码
        review=LLMReview(),                 # 真 LLM 归因
    )

    src_file = BASE / "samples/tiling/src/add_custom_tiling.cpp"
    result = fw.run("tiling", src_file)

    print("=" * 60)
    print("知识飞轮 · tiling 端到端（知识=桩，Coder/Review=真实 DeepSeek）")
    print("=" * 60)
    print(f"被测源码 : samples/tiling/src/add_custom_tiling.cpp")
    print(f"评测集   : samples/tiling/evalset/test_tiling.cpp（探针真实输出）")
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
    if tr.failures:
        print("失败详情 :")
        for f in tr.failures[:5]:
            print(f"  {f}")
    print()
    print(f"知识文档 : {cfg.knowledge_dir / ('tiling_v%d.md' % result['doc'].version)}")
    print(f"LLM 生成代码 : {result['code_path']}")


if __name__ == "__main__":
    main()
