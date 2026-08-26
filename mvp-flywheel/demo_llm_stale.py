#!/usr/bin/env python3
"""过时文档场景真 LLM 端到端：知识=预置解释型文档（不含源码，含过时点），
Coder/Review=真实 DeepSeek。

模拟真实场景：仓库里有一份解释型知识文档（滞后于源码），LLM Coder 必须
理解算法并补全过时点（tailNumLastCore 计算），写错则由 LLM Review 归因、
修订知识、重新生成。

用法:
  python3 demo_llm_stale.py
"""

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fw.config import Config
from fw.runner import KnowledgeFlywheel
from roles.llm_roles import DocKnowledgeGen, LLMCoder, LLMReview

BASE = Path(__file__).resolve().parent


def main():
    work = BASE / "samples/tiling/run_llm_stale"
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

    stale_doc = BASE / "samples/tiling/knowledge_stale/tiling_v1_stale.md"
    fw = KnowledgeFlywheel(
        cfg,
        knowledge_gen=DocKnowledgeGen(stale_doc),   # 预置解释型文档（桩，非 LLM）
        coder=LLMCoder(cfg=cfg, api_timeout=cfg.api_timeout),   # 真 LLM 写码（沙箱隔离）
        review=LLMReview(cfg=cfg, api_timeout=cfg.api_timeout), # 真 LLM 归因
    )

    src_file = BASE / "samples/tiling/src/add_custom_tiling.cpp"
    result = fw.run("tiling", src_file)

    print("=" * 60)
    print("知识飞轮 · 过时文档场景（知识=解释型文档，Coder/Review=真实 DeepSeek）")
    print("=" * 60)
    print(f"知识文档 : 预置解释型（含过时点：tailNumLastCore 缺失计算说明）")
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
    print(f"重复评测 : {tr.reps_count} 次  mean={tr.reps_mean:.3f} "
          f"var={tr.reps_variance:.4f} min={tr.reps_min:.2f} "
          f"unstable={tr.unstable}")
    if tr.failures:
        print("失败详情 :")
        for f in tr.failures[:5]:
            print(f"  {f}")
    print()
    print(f"知识文档 : {cfg.knowledge_dir / ('tiling_v%d.md' % result['doc'].version)}")
    print(f"LLM 生成代码 : {result['code_path']}")


if __name__ == "__main__":
    main()
