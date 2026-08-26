"""修订队列、不可丢历史 ledger 与确定性门禁状态机。"""

import copy
import json
from dataclasses import asdict

from fw.config import Config
from roles import Attribution, KnowledgeDoc


class CorrectionQueue:
    def __init__(self, cfg: Config, run_id: str = ""):
        self.cfg = cfg
        self.run_id = run_id
        self.ledger_path = cfg.ledger_path
        self._active = []
        self._history = []
        self._load()

    def _load(self):
        if not self.ledger_path.exists():
            return
        data = json.loads(self.ledger_path.read_text(encoding="utf-8"))
        self._active = data.get("active", data.get("pending", []))
        self._history = data.get("history", [])

    def _save(self):
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"schema_version": "correction-ledger.v1", "active": self._active, "history": self._history}
        temp = self.ledger_path.with_suffix(self.ledger_path.suffix + ".tmp")
        temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(self.ledger_path)

    def push(self, attribution: Attribution, round_number: int = 0, knowledge_version: int = 0):
        for correction in attribution.corrections:
            item = {
                "schema_version": "correction.v1",
                "run_id": self.run_id,
                "round": round_number,
                "id": correction.id,
                "knowledge_version": knowledge_version,
                "knowledge_path": correction.knowledge_path,
                "criterion": correction.criterion,
                "detail": correction.detail,
                "module": attribution.module,
                "status": "pending",
                "evidence": [],
            }
            self._active.append(item)
            self._history.append(dict(item, event="created"))
        self._save()

    def pop_pending(self) -> list:
        from roles import Correction
        return [
            Correction(id=item["id"], knowledge_path=item["knowledge_path"],
                       criterion=item["criterion"], detail=item.get("detail", ""))
            for item in self._active if item["status"] == "pending"
        ]

    def mark_done(self, corr_id: str, ok: bool, evidence: list | None = None):
        status = "done" if ok else "failed"
        for item in self._active:
            if item["id"] == corr_id and item["status"] == "pending":
                item["status"] = status
                item["evidence"] = list(evidence or [])
                self._history.append(dict(item, event="resolved"))
        self._active = [item for item in self._active if item["status"] == "pending"]
        self._save()

    def clear(self):
        """关闭活动队列但保留审计历史。"""
        for item in self._active:
            if item["status"] == "pending":
                item["status"] = "cancelled"
                self._history.append(dict(item, event="cancelled"))
        self._active = []
        self._save()

    @property
    def history(self) -> list:
        return copy.deepcopy(self._history)


def apply_revision(doc: KnowledgeDoc, corrections: list, revision_fn) -> KnowledgeDoc:
    if not corrections:
        return doc.clone()
    parent = doc.clone()
    working = doc.clone()
    revised = revision_fn(working, corrections)
    return revised.clone(
        version=parent.version + 1,
        parent_version=parent.version,
        status="draft",
    )


def decide(report, prev_confidence: "float | None", cfg: Config,
           budget_exhausted: bool = False) -> str:
    """确定性状态机：pass / iterate / rollback / unstable / stopped。"""
    if "ZERO_CASES" in report.reason_codes or "INCONSISTENT_TOTAL" in report.reason_codes:
        report.reason_codes.append("INVALID_EVALUATION")
        return "stopped"
    if not report.compile_ok:
        return "stopped" if budget_exhausted else "iterate"
    if not report.valid:
        report.reason_codes.append("INVALID_EVALUATION")
        return "stopped"
    if report.unstable:
        return "stopped" if budget_exhausted else "unstable"
    if prev_confidence is not None and report.confidence < prev_confidence:
        report.reason_codes.append("REGRESSION")
        return "rollback"
    if report.confidence >= cfg.pass_threshold:
        return "pass"
    if budget_exhausted:
        report.reason_codes.append("MAX_BUDGET")
        return "stopped"
    report.reason_codes.append("TRAIN_BELOW_THRESHOLD")
    return "iterate"
