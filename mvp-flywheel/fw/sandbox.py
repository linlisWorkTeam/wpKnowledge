"""Coder 最小权限路径沙箱。"""

from pathlib import Path

from fw.error_codes import EVALSET_LEAK, SOURCE_ACCESS_VIOLATION


class SandboxViolation(PermissionError):
    """路径访问被沙箱拦截。

    error_code 区分拦截原因（契约 §6）：
    - SOURCE_ACCESS_VIOLATION：触达源码区（src_dir）
    - EVALSET_LEAK：触达评测集/golden/holdout
    - 其他：不在白名单（默认 EVALSET_LEAK 语义由调用方按需覆盖）
    """

    def __init__(self, message: str, error_code: str = EVALSET_LEAK):
        super().__init__(message)
        self.error_code = error_code


def _resolve(path) -> Path:
    return Path(path).resolve(strict=False)


def _within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def build_sandbox(cfg) -> "Sandbox":
    cfg.validate()
    read_roots = {_resolve(cfg.knowledge_dir)}
    if cfg.interfaces_dir is not None:
        read_roots.add(_resolve(cfg.interfaces_dir))
    read_roots.update(_resolve(path) for path in cfg.allowed_read_dirs)

    write_roots = {_resolve(cfg.work_dir)}
    write_roots.update(_resolve(path) for path in cfg.allowed_write_dirs)
    denied = {_resolve(cfg.src_dir), _resolve(cfg.evalset_dir)}
    if cfg.private_evalset_dir is not None:
        denied.add(_resolve(cfg.private_evalset_dir))
    return Sandbox(read_roots, write_roots, denied)


class Sandbox:
    def __init__(self, allowed_read: set, allowed_write: set, denied: set):
        self.allowed_read = {_resolve(path) for path in allowed_read}
        self.allowed_write = {_resolve(path) for path in allowed_write}
        self.denied = {_resolve(path) for path in denied}

    def allowed_dirs(self) -> list:
        return sorted(str(path) for path in self.allowed_read)

    def _assert_not_denied(self, path: Path) -> None:
        denied_src = {_resolve(d) for d in self.denied}
        for denied in denied_src:
            if _within(path, denied):
                raise SandboxViolation(
                    f"沙箱拦截：{path} 位于禁止目录 {denied}",
                    error_code=SOURCE_ACCESS_VIOLATION)

    def assert_readable(self, path) -> Path:
        target = _resolve(path)
        self._assert_not_denied(target)
        if any(_within(target, root) for root in self.allowed_read):
            return target
        raise SandboxViolation(f"沙箱拦截读取：{target} 不在最小只读白名单内")

    def assert_writable(self, path) -> Path:
        target = _resolve(path)
        self._assert_not_denied(target)
        if any(_within(target, root) for root in self.allowed_write):
            return target
        raise SandboxViolation(f"沙箱拦截写入：{target} 不在本轮输出白名单内")

    def read_text(self, path, encoding: str = "utf-8") -> str:
        return self.assert_readable(path).read_text(encoding=encoding)


def read_header(cfg, module_hint: str = "", sandbox: Sandbox | None = None) -> str:
    """只从 interfaces_dir 读取公开接口；生产模式禁止源码回退。"""
    interface_dir = cfg.eval_include_dir()
    headers = sorted(Path(interface_dir).glob("*.h"))
    if module_hint:
        preferred = [header for header in headers if module_hint in header.stem]
        headers = preferred or headers
    if not headers:
        return ""
    header = headers[0]
    return (sandbox.read_text(header) if sandbox else header.read_text(encoding="utf-8"))
