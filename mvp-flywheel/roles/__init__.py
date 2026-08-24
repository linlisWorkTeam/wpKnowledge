"""角色接口定义（可插拔）。

MVP 用确定性桩实现（roles/stubs.py）；接入 codeagent 时实现同一接口即可替换。
对应《知识飞轮实现方案.md》§3 角色分工：
- 知识生成 Agent：源码 → 知识文档；唯一执笔者
- Coder Agent：知识 → 临时代码；不迭代、不验证、不读源码
- Review Agent：diff 定位 + 溯源归因 + 生成反馈；只读
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


# ---------- 数据结构 ----------

@dataclass
class KnowledgeDoc:
    """知识文档（OKF 知识卡，解释型 Markdown）。"""
    module: str
    version: int = 1
    content: str = ""
    sources: list = field(default_factory=list)  # [{file, symbol, lines}]
    score: float = 0.0
    status: str = "draft"  # draft / verified

    @property
    def path(self) -> str:
        return f"storage/knowledge/{self.module}_v{self.version}.md"


@dataclass
class EvalReport:
    """评测报告（自动化闭环产出）。"""
    module: str
    compile_ok: bool = False
    compile_errors: list = field(default_factory=list)
    passed: int = 0
    total: int = 0
    similarity: float = 0.0
    confidence: float = 0.0  # passed / total
    split: str = "train"     # train / holdout
    failures: list = field(default_factory=list)  # 失败用例详情（Review 归因依据）

    @property
    def passed_gate(self) -> bool:
        return self.compile_ok and self.confidence >= 0.8


@dataclass
class Correction:
    """修订指令（readlist 三字段：ID + 路径 + 判据）。"""
    id: str
    knowledge_path: str   # 知识段落路径
    criterion: str        # 验证判据
    detail: str = ""      # 自然语言解读


@dataclass
class Attribution:
    """Review 归因报告。"""
    module: str
    corrections: list = field(default_factory=list)
    summary: str = ""
    weak_spots: list = field(default_factory=list)  # 薄弱点


# ---------- 角色接口 ----------

class KnowledgeGenAgent(ABC):
    """知识生成 Agent：源码 → 知识文档。唯一执笔者。"""
    @abstractmethod
    def generate(self, module: str, src_file: Path, sources: list) -> KnowledgeDoc:
        ...

    @abstractmethod
    def revise(self, doc: KnowledgeDoc, corrections: list) -> KnowledgeDoc:
        ...


class CoderAgent(ABC):
    """Coder Agent：知识 → 临时代码。不读源码。"""
    @abstractmethod
    def generate_code(self, doc: KnowledgeDoc, out_path: Path) -> Path:
        ...


class ReviewAgent(ABC):
    """Review Agent：diff 定位 + 溯源归因 + 反馈。只读。"""
    @abstractmethod
    def attribute(self, module: str, doc: KnowledgeDoc, report: EvalReport) -> Attribution:
        ...
