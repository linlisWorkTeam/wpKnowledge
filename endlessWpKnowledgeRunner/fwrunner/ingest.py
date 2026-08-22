# -*- coding: utf-8 -*-
"""Acquire -> Consolidate pipeline: raw knowledge in, OKF cards out (gated).

Trigger entry point of the flywheel: fw_ingest / CLI ingest. Steps:
  1. read input (file / text / stdin), reuse existing frontmatter if present
  2. normalize into a concept card (draft) with OKF frontmatter
  3. score multi-signal; gate: pass -> verified merge (version-bumped),
     fail -> stays in drafts with weak points
  4. journal log, rebuild index, register ingested hash (for liveMode dedup)
"""
import json
import os
from typing import Any, Dict, List, Optional

from . import okf, util
from .config import Config
from .scorer import Scorer
from .store import Concept, Store

REQUIRED_META = ("name", "description", "sources")


class IngestResult:
    def __init__(self, name: str, status: str, score: float, gate: str,
                 report: Dict[str, Any], path: str, version: int, note: str):
        self.name = name
        self.status = status
        self.score = score
        self.gate = gate
        self.report = report
        self.path = path
        self.version = version
        self.note = note

    def to_dict(self) -> Dict[str, Any]:
        return {
            "concept": self.name,
            "status": self.status,
            "score": self.score,
            "gate": self.gate,
            "version": self.version,
            "path": self.path,
            "note": self.note,
            "report": self.report,
        }


class Ingester:
    def __init__(self, cfg: Config, store: Store, scorer: Scorer):
        self.cfg = cfg
        self.store = store
        self.scorer = scorer

    def run(self, content: Optional[str] = None, file_path: Optional[str] = None,
            name: Optional[str] = None, title: Optional[str] = None,
            description: Optional[str] = None, category: Optional[str] = None,
            tags: Optional[List[str]] = None, source: Optional[str] = None,
            force_draft: bool = False, pinned: bool = False,
            silent_file: Optional[str] = None,
            source_lines: Optional[str] = None) -> IngestResult:
        # 1. read input
        if file_path:
            if os.path.isabs(file_path):
                abs_path = file_path
            else:
                candidates = [self.cfg.resolve_repo_path(file_path),
                              os.path.join(self.cfg.root, file_path)]
                abs_path = next((p for p in candidates if os.path.isfile(p)), candidates[0])
            if not os.path.isfile(abs_path):
                raise FileNotFoundError("input file not found: %s" % abs_path)
            with open(abs_path, "r", encoding="utf-8") as f:
                content = f.read()
            auto_source = self.cfg.path_label(abs_path)
            # files inside a configured source dir are auto-marked handled so
            # liveMode scan does not re-list them
            if silent_file is None:
                for rel_dir in self.cfg.source_dirs:
                    base = rel_dir if os.path.isabs(rel_dir) else os.path.join(self.cfg.root, rel_dir)
                    try:
                        inside = os.path.commonpath([os.path.normpath(base), os.path.normpath(abs_path)])
                    except ValueError:
                        inside = None
                    if inside == os.path.normpath(base):
                        silent_file = auto_source
                        break
        else:
            auto_source = None
        if content is None:
            raise ValueError("ingest needs content or file_path")

        # 2. extract existing frontmatter (knowledge already in OKF form?)
        meta, body = okf.parse_frontmatter(content)
        if not body:
            raise ValueError("empty knowledge body")

        # 3. normalize meta
        concept_name = name or meta.get("name") or auto_source or ""
        if not concept_name:
            m = [ln for ln in body.split("\n") if ln.startswith("# ")]
            concept_name = m[0][2:].strip() if m else ""
        concept_name = util.slugify(concept_name)[:100] if concept_name else util.slugify(body[:40])
        meta["name"] = concept_name
        if title and not meta.get("title"):
            meta["title"] = title
        elif not meta.get("title") and meta.get("name"):
            meta["title"] = concept_name
        if description and not meta.get("description"):
            meta["description"] = description
        if category and not meta.get("category"):
            meta["category"] = category
        if tags and not meta.get("tags"):
            meta["tags"] = list(tags)
        if source and not meta.get("sources"):
            meta["sources"] = [source]
        elif source and isinstance(meta.get("sources"), str):
            meta["sources"] = [meta["sources"], source]
        sources = okf.normalize_sources(meta.get("sources"))
        if not sources and auto_source:
            sources = [{"path": auto_source, "pinned": pinned}]
        meta["sources"] = sources
        if pinned and sources:
            for s in sources:
                if not s.get("pinned"):
                    s["pinned"] = True
        if source_lines and sources:
            if not sources[0].get("lines"):
                sources[0]["lines"] = source_lines
        meta.setdefault("schema_version", "okf.v1")
        meta.setdefault("kind", "concept")
        meta.setdefault("status", "draft")
        meta.setdefault("verified", False)
        meta.setdefault("stale_after", "")
        meta.setdefault("platforms", [])
        meta.setdefault("tags", [])
        meta.setdefault("created_at", util.now_iso())
        meta["updated_at"] = util.now_iso()
        meta.pop("score", None)  # score is written by the runner only
        meta.pop("score_breakdown", None)
        meta.pop("confidence", None)

        existing = self.store.load_concept(concept_name)
        version = 1
        prev_score: Optional[float] = None
        prev_status: Optional[str] = None
        if existing is not None:
            prev_status = existing.status
            if existing.status == "verified":
                # upgrades must be version-bumped; old version snapshotted for rollback
                version = int(existing.meta.get("version", 1) or 1) + 1
                prev_score = existing.score
                meta["version"] = version
                self.store.snapshot_history(existing.name, existing.meta, existing.body)
                if existing.meta.get("created_at"):
                    meta["created_at"] = existing.meta["created_at"]
            else:
                # draft re-write keeps version 1 (never passed the gate)
                version = max(1, int(existing.meta.get("version", 1) or 1))
                meta["version"] = version
        else:
            meta["version"] = 1

        draft_concept = Concept(concept_name, "draft", self.store.card_path(concept_name, "draft"), meta, body)
        # 4. score + gate
        source_text: Optional[str] = None
        source_path: Optional[str] = None
        for s in sources:
            p = s.get("path", "")
            if p and not p.startswith(("http://", "https://")):
                candidate = p if os.path.isabs(p) else None
                for base in (self.cfg.root, os.path.dirname(self.cfg.root)):
                    if candidate is None:
                        candidate = os.path.join(base, p)
                    if os.path.isfile(candidate):
                        source_path = candidate
                        break
                if source_path:
                    with open(source_path, "r", encoding="utf-8") as f:
                        source_text = f.read()
                    break
        report = self.scorer.score_concept(draft_concept, source_text=source_text)

        # 5. persist
        status = "draft"
        note = ""
        if report.gate == "pass" and not force_draft:
            status = "verified"
            meta["status"] = "verified"
            meta["verified"] = True
            if prev_score is not None and prev_score > report.score:
                note = "score %.1f < 上一版 %.1f：已保留旧版快照于 history/，建议评估是否回滚（防污染约束）" % (
                    report.score, prev_score)
        else:
            meta["status"] = "draft"
            meta["verified"] = False
            if force_draft:
                note = "force_draft: 未过门禁也留在 drafts（门禁 %.1f < %s）" % (report.score, self.cfg.gate_threshold)
            elif prev_status == "verified":
                # Do not clobber a verified card with a worse candidate: keep the
                # verified version in concepts/, park the new content as a draft.
                note = "新版未过门禁（%.1f < %s）：保留已验证版本在 concepts/，本次内容退回 drafts/（防污染约束）" % (
                    report.score, self.cfg.gate_threshold)
                self.store.write_card(concept_name, "draft", meta, body,
                                      action="ingest:draft", detail="score=%.1f gate=fail (supersedes verified)" % report.score)
                self.store.register_ingested(util.sha256_text(body), concept_name)
                self.store.rebuild_index()
                return IngestResult(concept_name, "verified", report.score, "fail",
                                    report.to_dict(),
                                    self.store.card_path(concept_name, "verified"),
                                    version, note)
        meta["score"] = report.score
        meta["confidence"] = report.confidence
        meta["score_breakdown"] = {k: v for k, v in report.signals.items() if v is not None}
        path = self.store.write_card(concept_name, status, meta, body,
                                     action="ingest:%s" % status,
                                     detail="score=%.1f gate=%s" % (report.score, report.gate))
        self.store.register_ingested(util.sha256_text(body), concept_name)
        if silent_file:
            state = self.store.read_state()
            files = state.setdefault("files", {})
            full_path = self.cfg.resolve_repo_path(silent_file)
            files[silent_file] = {
                "hash": util.sha256_file(full_path) if os.path.isfile(full_path) else "",
                "concept": concept_name, "ts": util.now_iso(),
            }
            self.store.write_state(state)
        self.store.rebuild_index()
        self.store.append_log(action="index rebuilt", concept=concept_name,
                              score=report.score, detail="status=%s" % status)
        return IngestResult(concept_name, status, report.score, report.gate,
                            report.to_dict(), path, version, note)


def score_one(cfg: Config, store: Store, scorer: Scorer, name: str) -> Dict[str, Any]:
    concept = store.load_concept(name)
    if concept is None:
        raise KeyError("concept not found: %s" % name)
    report = scorer.score_concept(concept)
    # persist updated score fields
    meta = dict(concept.meta)
    meta["score"] = report.score
    meta["confidence"] = report.confidence
    meta["score_breakdown"] = {k: v for k, v in report.signals.items() if v is not None}
    store.write_card(concept.name, concept.status, meta, concept.body,
                     action="rescore", detail="score=%.1f gate=%s" % (report.score, report.gate))
    return report.to_dict()


def score_all(cfg: Config, store: Store, scorer: Scorer,
              statuses: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    out = []
    for c in store.list_concepts(statuses=statuses):
        try:
            out.append(score_one(cfg, store, scorer, c.name))
        except Exception as exc:  # noqa: BLE001 - per-card isolation
            out.append({"concept": c.name, "error": str(exc)})
    return out
