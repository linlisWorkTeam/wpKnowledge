"""知识飞轮配置与生产模式约束。"""

from dataclasses import dataclass, field
from pathlib import Path


class ConfigError(ValueError):
    """配置违反 SDD 约束。"""


@dataclass
class Config:
    # --- 运行模式 ---
    mode: str = "development"                  # development | production | experimental

    # --- 路径 ---
    src_dir: Path = Path("samples/tiling/src")
    interfaces_dir: Path | None = None
    evalset_dir: Path = Path("samples/tiling/evalset")
    private_evalset_dir: Path | None = None
    work_dir: Path = Path("data")
    knowledge_dir: Path = Path("storage/knowledge")  # 只存已接受知识
    ledger_path: Path = field(default_factory=lambda: Path("storage/ledger.json"))
    protected_paths: list = field(default_factory=list)

    # --- 评测与门禁 ---
    compiler: str = "g++"
    compile_flags: list = field(
        default_factory=lambda: ["-Wall", "-Werror", "-std=c++11", "-I{interfaces_dir}"]
    )
    holdout_ratio: float = 0.2
    require_holdout: bool = False
    pass_threshold: float = 0.8
    variance_threshold: float = 0.02
    max_rounds: int = 5
    repeat_generation: int = 1              # production 必须 >= 5
    repeat_eval: int = 5                    # 同一生成代码的重复执行次数
    max_seconds: float | None = None
    max_cost: float | None = None

    # --- 沙箱隔离 ---
    allowed_read_dirs: list = field(default_factory=list)
    allowed_write_dirs: list = field(default_factory=list)

    # --- 模型 ---
    model_provider: str = "stub"             # stub | codeagent | sdk | deepseek
    model_id: str = "GLM-5.1"
    codeagent_command: list = field(
        default_factory=lambda: ["codeagent", "--model", "GLM-5.1", "--json"]
    )
    api_timeout: int = 180
    max_doc_chars: int = 6000
    knowledge_chunk: bool = True

    # --- 评测集兼容 ---
    evalset_format: str = "auto"
    native_test_glob: str = "test_*"

    # --- 溯源 ---
    source_commit: str = ""
    evalset_version: str = "unversioned"
    prompt_version: str = "unversioned"

    @property
    def production(self) -> bool:
        return self.mode == "production"

    def resolve(self, base: Path) -> "Config":
        """把相对路径解析到 base 下；不隐式放宽安全约束。"""
        base = Path(base).resolve()
        for name in ("src_dir", "evalset_dir", "work_dir", "knowledge_dir", "ledger_path"):
            p = Path(getattr(self, name))
            if not p.is_absolute():
                p = base / p
            setattr(self, name, p.resolve())
        for name in ("interfaces_dir", "private_evalset_dir"):
            p = getattr(self, name)
            if p is not None:
                p = Path(p)
                if not p.is_absolute():
                    p = base / p
                setattr(self, name, p.resolve())
        self.allowed_read_dirs = [self._resolve_optional(base, p) for p in self.allowed_read_dirs]
        self.allowed_write_dirs = [self._resolve_optional(base, p) for p in self.allowed_write_dirs]
        self.protected_paths = [self._resolve_optional(base, p) for p in self.protected_paths]
        return self

    @staticmethod
    def _resolve_optional(base: Path, value) -> Path:
        p = Path(value)
        return (p if p.is_absolute() else base / p).resolve()

    def eval_include_dir(self) -> Path:
        """评测编译使用公开接口；生产模式禁止回退源码目录。"""
        if self.interfaces_dir is not None:
            return Path(self.interfaces_dir)
        if self.production:
            raise ConfigError("production 模式必须显式配置 interfaces_dir，禁止回退 src_dir")
        return Path(self.src_dir)

    def validate(self) -> "Config":
        """启动前 fail fast 校验。"""
        if self.mode not in {"development", "production", "experimental"}:
            raise ConfigError(f"未知 mode: {self.mode}")
        if not 0.0 < self.pass_threshold <= 1.0:
            raise ConfigError("pass_threshold 必须在 (0, 1] 范围")
        if not 0.0 <= self.holdout_ratio < 1.0:
            raise ConfigError("holdout_ratio 必须在 [0, 1) 范围")
        if self.repeat_eval < 1 or self.repeat_generation < 1:
            raise ConfigError("repeat_eval 和 repeat_generation 必须 >= 1")
        if self.max_rounds < 1:
            raise ConfigError("max_rounds 必须 >= 1")
        if self.variance_threshold < 0:
            raise ConfigError("variance_threshold 不能为负数")
        if self.evalset_format not in {"auto", "json", "native"}:
            raise ConfigError(f"未知 evalset_format: {self.evalset_format}")

        src = Path(self.src_dir).resolve()
        if self.interfaces_dir is not None:
            interfaces = Path(self.interfaces_dir).resolve()
            if src == interfaces or _is_relative_to(src, interfaces) or _is_relative_to(interfaces, src):
                if self.production:
                    raise ConfigError("production 的 src_dir 与 interfaces_dir 必须物理分离")

        if self.production:
            self.eval_include_dir()  # 强制 interfaces_dir
            if not self.require_holdout:
                raise ConfigError("production 模式必须 require_holdout=True")
            if self.repeat_generation < 5:
                raise ConfigError("production 模式 repeat_generation 必须 >= 5")
            if self.repeat_eval < 1:
                raise ConfigError("production 模式 repeat_eval 必须 >= 1")
            if self.model_provider not in {"codeagent", "sdk"}:
                raise ConfigError("production 模式只允许 codeagent 或批准的 sdk provider")
            if self.model_id.upper().replace(" ", "") not in {"GLM-5.1", "GLM5.1"}:
                raise ConfigError("production 模式模型必须为 GLM 5.1")
            if not self.source_commit:
                raise ConfigError("production 模式必须提供 source_commit")
        if self.model_provider == "deepseek" and self.mode != "experimental":
            raise ConfigError("DeepSeek 仅允许在 experimental 模式使用")
        return self


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False
