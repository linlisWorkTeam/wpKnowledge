"""修订闭环：pending_corrections 队列 + revise 流程 + 版本控制/回滚。

对应《codeagent执行手册》§5：
1. Review 归因报告入 pending_corrections 队列
2. fw revise 流程：读反馈 → sources 反查 → 修订 → 走评测 → 通过则版本升级，未过则不合并
3. 修订指令结构化（readlist 三字段：ID + 路径 + 判据）
验收：修订后重测；门禁通过才合并；分数下降自动回滚。
"""

import json
from pathlib import Path

from fw.config import Config
from roles import Attribution, KnowledgeDoc


class CorrectionQueue:
    """pending_corrections 队列（持久化到 ledger.json）。"""

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.ledger_path = cfg.ledger_path
        self._items = []
        self._load()

    def _load(self):
        if self.ledger_path.exists():
            data = json.loads(self.ledger_path.read_text())
            self._items = data.get("pending", [])

    def _save(self):
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        self.ledger_path.write_text(json.dumps({"pending": self._items}, ensure_ascii=False, indent=2))

    def push(self, attribution: Attribution):
        for c in attribution.corrections:
            item = {
                "id": c.id,
                "knowledge_path": c.knowledge_path,
                "criterion": c.criterion,
                "detail": c.detail,
                "module": attribution.module,
                "status": "pending",
            }
            self._items.append(item)
        self._save()

    def pop_pending(self) -> list:
        """返回待处理修订（Correction 对象）。"""
        from roles import Correction
        return [Correction(id=i["id"],
                           knowledge_path=i["knowledge_path"],
                           criterion=i["criterion"],
                           detail=i["detail"])
                for i in self._items if i["status"] == "pending"]

    def mark_done(self, corr_id: str, ok: bool):
        for i in self._items:
            if i["id"] == corr_id:
                i["status"] = "done" if ok else "failed"
        self._save()

    def clear(self):
        self._items = []
        self._save()


def apply_revision(doc: KnowledgeDoc, corrections: list, revision_fn) -> KnowledgeDoc:
    """执行修订：调用知识生成 Agent 的 revise，版本 +1。"""
    if not corrections:
        return doc
    new_doc = revision_fn(doc, corrections)
    new_doc.version = doc.version + 1
    new_doc.status = "draft"
    return new_doc


def decide(report, prev_confidence: "float | None", cfg: Config) -> str:
    """编排层决策（状态机）：通过 / 迭代 / 回滚。

    - confidence >= 门限 → 通过
    - confidence < 门限 且 > 上一轮 → 迭代
    - confidence < 上一轮 → 回滚（防污染）
    """
    if report.confidence >= cfg.pass_threshold:
        return "pass"
    if prev_confidence is None or report.confidence >= prev_confidence:
        return "iterate"
    return "rollback"
