#!/usr/bin/env python3
"""缺陷知识场景真 LLM 端到端：知识=预置含缺陷公式的文档（numPerCore/tail 公式错误），
Coder/Review=真实 DeepSeek。

演示飞轮迭代闭环：
R1 按缺陷知识生成代码 → 评测失败 → Review 归因（定位缺陷段落）→ 修订知识 v2
→ R2 重新生成 → 评测通过 → 发布。

用法:
  python3 demo_llm_iterative.py
"""

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fw.config import Config
from fw.runner import KnowledgeFlywheel
from roles.llm_roles import DocKnowledgeGen, LLMCoder, LLMReview
from roles.providers import DeepSeekProvider

BASE = Path(__file__).resolve().parent


def main():
    work = BASE / "samples/tiling/run_llm_iterative"
    if work.exists():
        shutil.rmtree(work)
    cfg = Config(
        mode="experimental",
        src_dir=BASE / "samples/tiling/src",
        interfaces_dir=BASE / "samples/tiling/interfaces",
        evalset_dir=BASE / "samples/tiling/evalset",
        work_dir=work / "data",
        knowledge_dir=work / "storage/knowledge",
        compiler="g++",
        compile_flags=["-Wall", "-Werror", "-std=c++11", "-I{src_dir}"],
        model_provider="deepseek",
        model_id="deepseek-v4-flash",
        max_rounds=3,
    ).resolve(BASE)

    provider = DeepSeekProvider(model=cfg.model_id)

    buggy_doc = BASE / "samples/tiling/knowledge_buggy/tiling_v1_buggy.md"
    fw = KnowledgeFlywheel(
        cfg,
        knowledge_gen=DocKnowledgeGen(buggy_doc),   # 预置缺陷知识（桩）
        coder=LLMCoder(cfg=cfg, api_timeout=cfg.api_timeout, provider=provider),
        review=LLMReview(cfg=cfg, api_timeout=cfg.api_timeout, provider=provider),
    )

    src_file = BASE / "samples/tiling/src/add_custom_tiling.cpp"
    result = fw.run("tiling", src_file)

    print("=" * 60)
    print("知识飞轮 · 缺陷知识迭代场景（知识=缺陷公式，Coder/Review=真实 DeepSeek）")
    print("=" * 60)
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
    print(f"知识版本 : v{result['doc'].version} (status={result['doc'].status})")
    print(f"run_root : {result['run_root']}")

    # 打印各轮产物清单
    run_root = result["run_root"]
    print()
    print("产物清单 :")
    for p in sorted(run_root.rglob("*")):
        if p.is_file():
            print(f"  {p.relative_to(run_root)}")


if __name__ == "__main__":
    main()
