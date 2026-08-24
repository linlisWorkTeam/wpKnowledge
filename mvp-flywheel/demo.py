#!/usr/bin/env python3
"""端到端演示：跑一次完整知识飞轮。

用法：
  python3 demo.py                # 正常流程（一轮通过）
  python3 demo.py --bad-coder    # 注入缺陷的 Coder，演示迭代修订闭环
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fw.config import Config
from fw.runner import KnowledgeFlywheel
from roles.stubs import StubCoder

BASE = Path(__file__).resolve().parent


def main():
    args = [a for a in sys.argv if not a.startswith("--")]
    bad = "--bad-coder" in sys.argv
    evalset_override = None
    if "--evalset" in sys.argv:
        idx = sys.argv.index("--evalset")
        if idx + 1 < len(sys.argv):
            evalset_override = Path(sys.argv[idx + 1])
    work = Path(tempfile.mkdtemp(prefix="fw_demo_"))
    cfg = Config(
        src_dir=BASE / "samples/src",
        evalset_dir=evalset_override or (BASE / "samples/evalset"),
        work_dir=work / "data",
        knowledge_dir=work / "storage/knowledge",
    ).resolve(BASE)

    if bad:
        def broken(code: str) -> str:
            return (code.replace("return a + b;", "return a * b;")
                        .replace("if (x < lo) return lo;\n    if (x > hi) return hi;", ""))
        fw = KnowledgeFlywheel(cfg, coder=StubCoder(defect_fn=broken))
    else:
        fw = KnowledgeFlywheel(cfg)

    result = fw.run("calc", BASE / "samples/src/calc.c")

    print("=" * 60)
    print("知识飞轮 MVP 端到端演示")
    print("=" * 60)
    print(f"被测模块 : calc (samples/src/calc.c)")
    if evalset_override:
        print(f"评测集   : {evalset_override}（用户本地，--evalset 指定）")
    else:
        print(f"评测集   : samples/evalset（示例）")
    if bad:
        print("Coder    : 注入缺陷（add→乘法、clamp 无边界）")
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
    hr = result["holdout_report"]
    if hr:
        print(f"holdout评测: passed={hr.passed}/{hr.total} confidence={hr.confidence:.2f} "
              f"(只报告，不参与反馈)")
    print()
    print(f"知识文档 : {cfg.knowledge_dir / ('calc_v%d.md' % result['doc'].version)}")
    print(f"评测报告 : {work}/data/reports/")
    print(f"生成代码 : {result['code_path']}")


if __name__ == "__main__":
    main()
