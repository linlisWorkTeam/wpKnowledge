#!/usr/bin/env python3
"""跨平台验证 Coder 的源码隔离与最小读写权限。"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fw.config import Config
from fw.sandbox import SandboxViolation, build_sandbox


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="flywheel-sandbox-") as temp:
        root = Path(temp)
        flywheel = root / "flywheel"
        src_biz = root / "src-biz"
        interfaces = flywheel / "interfaces"
        knowledge = flywheel / "knowledge"
        work = flywheel / "work"
        evalset = flywheel / "eval-private"
        for directory in (src_biz, interfaces, knowledge, work, evalset):
            directory.mkdir(parents=True)

        source = src_biz / "secret.cpp"
        source.write_text("int secret() { return 42; }", encoding="utf-8")
        header = interfaces / "secret.h"
        header.write_text("int secret();", encoding="utf-8")
        doc = knowledge / "secret_v1.md"
        doc.write_text("# secret", encoding="utf-8")

        cfg = Config(
            src_dir=src_biz,
            interfaces_dir=interfaces,
            evalset_dir=evalset,
            work_dir=work,
            knowledge_dir=knowledge,
        ).resolve(Path.cwd())
        sandbox = build_sandbox(cfg)

        assert sandbox.read_text(doc) == "# secret"
        assert sandbox.read_text(header) == "int secret();"
        assert sandbox.assert_writable(work / "round-1/code.cpp")

        for forbidden in (source, work / "old-report.json", evalset / "holdout.json"):
            try:
                sandbox.assert_readable(forbidden)
            except SandboxViolation:
                pass
            else:
                raise AssertionError(f"沙箱错误放行: {forbidden}")

        try:
            sandbox.assert_readable(work / ".." / ".." / "src-biz" / "secret.cpp")
        except SandboxViolation:
            pass
        else:
            raise AssertionError("路径穿越未被拦截")

    print("PASS: Coder 只能读取知识/接口并写入本轮工作区，源码与评测私有数据均被拦截")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

