"""holdout 分层：按模块名哈希划分 train / holdout。

对应《codeagent执行手册》§4：
- holdout_ratio = 0.2
- holdout 模块用例不参与反馈迭代
- fw_eval --holdout 只报告不写回
"""

import hashlib


def _split_key(module: str, ratio: float) -> str:
    """模块名哈希 → train/holdout。同一模块永远落同一分区。"""
    h = hashlib.sha256(module.encode()).hexdigest()
    bucket = int(h, 16) % 1000
    return "holdout" if bucket < ratio * 1000 else "train"


def split_cases(cases: list, ratio: float = 0.2) -> dict:
    """把 cases 划分成 {'train': [...], 'holdout': [...]}。"""
    result = {"train": [], "holdout": []}
    for c in cases:
        split = c.get("split") or _split_key(c.get("module", ""), ratio)
        result[split].append(c)
    return result


def is_holdout(case: dict, ratio: float = 0.2) -> bool:
    """单条 case 是否 holdout（用例显式标注优先，否则按模块哈希）。"""
    split = case.get("split")
    if split:
        return split == "holdout"
    return _split_key(case.get("module", ""), ratio) == "holdout"
