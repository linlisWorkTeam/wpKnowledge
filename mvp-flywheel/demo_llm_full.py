#!/usr/bin/env python3
"""全流程真 LLM 端到端（tiling 模块）：知识生成 / Coder / Review 全部走真实 DeepSeek。

严格按飞轮流程：
- 知识生成 Agent（LLMKnowledgeGen）：读源码 → 生成**解释型知识文档（无源码原文）**
- Coder Agent（LLMCoder）：只读知识 + 接口头文件 → 写代码（不接触源码实现）
- 评测闭环（代码）：编译必过 + 测试主判（探针真实输出）
- Review Agent（LLMReview）：失败详情 → 归因 + 修订指令
- 修订：知识版本 +1 → 重新生成代码 → 重测

用法:
  python3 demo_llm_full.py
"""

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fw.config import Config
from fw.runner import KnowledgeFlywheel
from roles.llm_roles import LLMCoder, LLMKnowledgeGen, LLMReview

BASE = Path(__file__).resolve().parent


def main():
    work = BASE / "samples/tiling/run_llm_full"
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
        knowledge_gen=LLMKnowledgeGen(),   # 真 LLM：源码 → 解释型知识（无源码）
        coder=LLMCoder(),                  # 真 LLM：知识 → 代码
        review=LLMReview(),                # 真 LLM：失败 → 归因
    )

    src_file = BASE / "samples/tiling/src/add_custom_tiling.cpp"
    result = fw.run("tiling", src_file)

    print("=" * 60)
    print("知识飞轮 · 全流程真 LLM（知识生成/Coder/Review = DeepSeek）")
    print("=" * 60)
    print(f"被测源码 : samples/tiling/src/add_custom_tiling.cpp")
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
    doc = result["doc"]
    print(f"知识文档 : {cfg.knowledge_dir / ('tiling_v%d.md' % doc.version)}")
    print(f"LLM 生成代码 : {result['code_path']}")


if __name__ == "__main__":
    main()
