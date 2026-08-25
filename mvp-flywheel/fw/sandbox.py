"""沙箱隔离：Coder 进程的路径访问白名单校验（防作弊核心）。

对应《codeagent执行手册》§0.1 防作弊红线：
- 源码在飞轮外（src-biz/ 只读），Coder 物理摸不到源码
- Coder 只能读：知识库（knowledge_dir）+ 接口头文件副本（interfaces_dir）+ 工作区（work_dir）
- src_dir（源码目录）永远禁止读取

用法：
    from fw.sandbox import build_sandbox, SandboxViolation
    sb = build_sandbox(cfg)
    sb.assert_readable("/flywheel/knowledge/tiling_v1.md")   # OK
    sb.assert_readable("/src-biz/add_custom_tiling.cpp")     # 抛 SandboxViolation
"""

from pathlib import Path


class SandboxViolation(PermissionError):
    """Coder 试图读取白名单外路径（视为作弊企图）。"""


def build_sandbox(cfg) -> "Sandbox":
    """按 Config 构建沙箱。

    白名单 = allowed_read_dirs（显式配置，优先）∪ knowledge_dir ∪ interfaces_dir ∪ work_dir。
    src_dir 永远不在白名单（即使配置 allowed_read_dirs 包含也不放行——源码红线）。
    """
    allow = set()
    for d in cfg.allowed_read_dirs or []:
        allow.add(str(Path(d).resolve()))
    allow.add(str(Path(cfg.knowledge_dir).resolve()))
    allow.add(str(Path(cfg.eval_include_dir()).resolve()))  # interfaces_dir 或回退 src_dir
    allow.add(str(Path(cfg.work_dir).resolve()))
    deny = {str(Path(cfg.src_dir).resolve())}
    return Sandbox(allowed=allow, denied=deny)


class Sandbox:
    """路径白名单沙箱。resolve 后比较，防 .. 绕过。"""

    def __init__(self, allowed: set, denied: set):
        self.allowed = {str(Path(p).resolve()) for p in allowed}
        self.denied = {str(Path(p).resolve()) for p in denied}

    def _norm(self, p) -> str:
        return str(Path(p).resolve())

    def allowed_dirs(self) -> list:
        return sorted(self.allowed)

    def assert_readable(self, path) -> Path:
        """校验路径可读：必须在白名单内、且不在黑名单内。返回规范路径。"""
        p = Path(path)
        # 文件可能不存在（如生成代码路径），先取父目录判断
        target = self._norm(p)
        parent = self._norm(p.parent if p.suffix else p)
        for denied in self.denied:
            if target.startswith(denied + "/") or target == denied:
                raise SandboxViolation(
                    f"沙箱拦截：{path} 在禁止目录 {denied} 内（源码红线，禁止读取）")
        for allowed in self.allowed:
            if parent.startswith(allowed + "/") or parent == allowed:
                return p
            # 文件本身在白名单目录内（含不存在的生成路径）
            if target.startswith(allowed + "/"):
                return p
        raise SandboxViolation(
            f"沙箱拦截：{path} 不在白名单 {sorted(self.allowed)} 内")

    def read_text(self, path, encoding: str = "utf-8") -> str:
        """白名单内读取文件（带校验）。"""
        self.assert_readable(path)
        return Path(path).read_text(encoding=encoding)


def read_header(cfg, module_hint: str = "") -> str:
    """从 interfaces_dir（或回退 src_dir）读取接口头文件内容。

    注意：仅读头文件（接口定义，非实现），用于 Coder 的 #include 提示。
    这是 Coder 唯一允许接触的"源码形态"——头文件是接口契约，不是实现。
    """
    inc = Path(cfg.eval_include_dir())
    for h in sorted(inc.glob("*.h")):
        return h.read_text()
    return ""
