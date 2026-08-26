"""角色接口和跨组件数据契约。"""

import copy
import hashlib
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class KnowledgeDoc:
    """带稳定溯源与版本关系的知识候选。"""

    module: str
    version: int = 1
    content: str = ""
    sources: list = field(default_factory=list)
    status: str = "draft"  # draft | verified | rejected
    source_commit: str = ""
    parent_version: int | None = None
    run_id: str = ""

    @property
    def path(self) -> str:
        return f"storage/knowledge/{self.module}_v{self.version}.md"

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.render().encode("utf-8")).hexdigest()

    def clone(self, **changes) -> "KnowledgeDoc":
        result = copy.deepcopy(self)
        for name, value in changes.items():
            setattr(result, name, value)
        return result

    def render(self) -> str:
        """渲染最小 OKF 风格 frontmatter；正文保持 Markdown。"""
        metadata = {
            "title": self.module,
            "status": self.status,
            "version": self.version,
            "source_commit": self.source_commit,
            "parent_version": self.parent_version,
            "run_id": self.run_id,
            "sources": self.sources,
        }
        # JSON 是 YAML 1.2 的合法子集，避免引入额外依赖。
        return "---\n" + json.dumps(metadata, ensure_ascii=False, indent=2) + "\n---\n\n" + self.content


@dataclass
class EvalReport:
    """自动评测报告；门禁必须显式传入配置阈值。"""

    module: str
    compile_ok: bool = False
    compile_errors: list = field(default_factory=list)
    passed: int = 0
    total: int = 0
    similarity: float = 0.0
    confidence: float = 0.0
    split: str = "train"
    failures: list = field(default_factory=list)

    # 重复执行统计
    repetitions: list = field(default_factory=list)
    reps_count: int = 0
    reps_mean: float = 0.0
    reps_variance: float = 0.0
    reps_min: float = 0.0
    unstable: bool = False

    # 多次生成统计
    generation_results: list = field(default_factory=list)
    generation_count: int = 0

    # 审计
    schema_version: str = "eval-report.v1"
    run_id: str = ""
    round: int = 0
    knowledge_version: int = 0
    knowledge_sha256: str = ""
    evalset_version: str = "unversioned"
    source_commit: str = ""
    environment: dict = field(default_factory=dict)
    decision: str = ""
    reason_codes: list = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return self.total > 0 and self.reps_count > 0

    def passes(self, threshold: float) -> bool:
        return self.valid and self.compile_ok and not self.unstable and self.confidence >= threshold

    def public_copy(self) -> "EvalReport":
        """给 Review 的脱敏报告；holdout 只保留聚合结果。"""
        result = copy.deepcopy(self)
        if self.split == "holdout":
            result.failures = []
            result.repetitions = []
            result.generation_results = []
        return result

    def as_dict(self, public: bool = False) -> dict:
        report = self.public_copy() if public else self
        return {
            "schema_version": report.schema_version,
            "run_id": report.run_id,
            "round": report.round,
            "module": report.module,
            "knowledge": {"version": report.knowledge_version, "sha256": report.knowledge_sha256},
            "evalset": {
                "version": report.evalset_version,
                "source_commit": report.source_commit,
                "split": report.split,
            },
            "environment": report.environment,
            "compile": {"passed": report.compile_ok, "errors": report.compile_errors},
            "passed": report.passed,
            "total": report.total,
            "confidence": report.confidence,
            "repetitions": report.repetitions,
            "generation_repetitions": report.generation_results,
            "statistics": {
                "count": report.reps_count,
                "mean": report.reps_mean,
                "variance": report.reps_variance,
                "min": report.reps_min,
                "unstable": report.unstable,
            },
            "failures": report.failures,
            "diagnostics": {"text_similarity": report.similarity},
            "decision": report.decision,
            "reason_codes": report.reason_codes,
        }


@dataclass
class Correction:
    id: str
    knowledge_path: str
    criterion: str
    detail: str = ""


@dataclass
class Attribution:
    module: str
    corrections: list = field(default_factory=list)
    summary: str = ""
    weak_spots: list = field(default_factory=list)


class KnowledgeGenAgent(ABC):
    @abstractmethod
    def generate(self, module: str, src_file: Path, sources: list) -> KnowledgeDoc:
        ...

    @abstractmethod
    def revise(self, doc: KnowledgeDoc, corrections: list) -> KnowledgeDoc:
        ...


class CoderAgent(ABC):
    @abstractmethod
    def generate_code(self, doc: KnowledgeDoc, out_path: Path) -> Path:
        ...


class ReviewAgent(ABC):
    @abstractmethod
    def attribute(self, module: str, doc: KnowledgeDoc, report: EvalReport) -> Attribution:
        ...
