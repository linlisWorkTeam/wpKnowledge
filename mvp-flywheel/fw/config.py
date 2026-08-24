"""知识飞轮 MVP 配置。

对应《codeagent执行手册》P0 要求：
- 评测闭环：编译必过 + 测试主判 + 相似度辅助
- holdout 分层：holdout_ratio = 0.2
- 修订闭环：pending_corrections 队列 + revise 流程
"""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Config:
    # --- 路径 ---
    src_dir: Path = Path("samples/src")          # 被测源码（C/C++）
    evalset_dir: Path = Path("samples/evalset")  # 评测集
    work_dir: Path = Path("data")                # 运行时产物
    knowledge_dir: Path = Path("storage/knowledge")  # 知识库（OKF 知识卡）

    # --- 评测 ---
    compiler: str = "gcc"                        # C 编译器；C++ 用 g++
    compile_flags: list = field(
        default_factory=lambda: ["-Wall", "-Werror", "-std=c11", "-I{src_dir}"]
    )
    holdout_ratio: float = 0.2                   # holdout 比例
    pass_threshold: float = 0.8                  # 门禁阈值（置信度 ≥ 0.8 通过）
    max_rounds: int = 5                          # 迭代轮次上限
    repeat_eval: int = 3                         # 重复评测次数（设计建议 ≥5，MVP 用 3 节省时间）

    # --- 评测集兼容（用户本地测试集）---
    # evalset_format:
    #   auto   - 自动检测（有 cases/*.json → json；有 test_*.c/.cpp → native）
    #   json   - JSON cases（自动生成 C 测试驱动）
    #   native - 原生 C/C++ 测试文件（用户本地测试集，直接编译运行，打印 PASS n/total）
    evalset_format: str = "auto"
    native_test_glob: str = "test_*"              # 原生测试文件匹配（test_*.c / test_*.cpp，可用 *.c / *.cpp）

    # --- 修订闭环 ---
    ledger_path: Path = field(default_factory=lambda: Path("storage/ledger.json"))

    def resolve(self, base: Path) -> "Config":
        """把相对路径解析到 base 下。"""
        for name in ("src_dir", "evalset_dir", "work_dir", "knowledge_dir", "ledger_path"):
            p = getattr(self, name)
            if not p.is_absolute():
                setattr(self, name, base / p)
        return self
