# -*- coding: utf-8 -*-
"""Controlled OKF knowledge-base store.

Only this module writes the knowledge base. The runner code lives in the
neighbouring endlessWpKnowledgeRunner directory; this store is the separate,
git-reviewable OKF bundle (concepts, drafts, history and governance runtime).
"""
import json
import os
import tempfile
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from . import okf
from .config import Config
from .util import now_iso, slugify

CARD_SUFFIX = ".md"


class Concept:
    def __init__(self, name: str, status: str, path: str, meta: Dict[str, Any], body: str):
        self.name = name
        self.status = status
        self.path = path
        self.meta = meta
        self.body = body

    @property
    def score(self) -> Optional[float]:
        v = self.meta.get("score")
        try:
            return float(v) if v is not None else None
        except (TypeError, ValueError):
            return None

    @property
    def category(self) -> str:
        return str(self.meta.get("category", "") or "")

    def to_dict(self, include_body: bool = False) -> Dict[str, Any]:
        d = dict(self.meta)
        d["name"] = self.name
        d["status"] = self.status
        d["path"] = self.path
        if include_body:
            d["body"] = self.body
        return d


class Store:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.root = cfg.store_dir
        self.drafts_dir = os.path.join(self.root, "drafts")
        self.concepts_dir = os.path.join(self.root, "concepts")
        self.history_dir = os.path.join(self.root, "history")
        self.runtime_dir = os.path.join(self.root, "runtime")
        self.jury_dir = os.path.join(self.runtime_dir, "jury")
        self.index_path = os.path.join(self.root, "index.md")
        self.log_path = os.path.join(self.runtime_dir, "log.md")
        self.ledger_path = os.path.join(self.runtime_dir, "ledger.json")
        state_file = str(cfg.get("livemode", {}).get("state_file", "runtime/livemode-state.json"))
        self.state_path = state_file if os.path.isabs(state_file) else os.path.join(self.root, state_file)
        self._ensure()

    def _ensure(self) -> None:
        for d in (self.root, self.drafts_dir, self.concepts_dir, self.history_dir, self.runtime_dir, self.jury_dir):
            os.makedirs(d, exist_ok=True)
        for p in (self.index_path, self.log_path):
            if not os.path.exists(p):
                os.makedirs(os.path.dirname(p), exist_ok=True)
                with open(p, "w", encoding="utf-8") as f:
                    f.write("")
        if not os.path.exists(self.ledger_path):
            self._write_ledger({"concepts": {}, "ingested_hashes": {}, "feedback": []})

    @staticmethod
    def _atomic_write(path: str, text: str) -> None:
        """Write a complete file before replacing the published version."""
        directory = os.path.dirname(path) or "."
        os.makedirs(directory, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=".write-", suffix=".tmp", dir=directory)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
                f.write(text)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    @staticmethod
    def _validate_name(name: str) -> str:
        safe = slugify(name)
        if not safe or safe != name or len(safe) > 100:
            raise ValueError("concept name must be a slug (a-z, 0-9, '-' or '_')")
        return safe

    # ---------------- card paths ----------------
    def card_path(self, name: str, status: str) -> str:
        self._validate_name(name)
        if status not in ("verified", "draft"):
            raise ValueError("card status must be draft or verified")
        base = self.concepts_dir if status == "verified" else self.drafts_dir
        return os.path.join(base, name + CARD_SUFFIX)

    def history_path(self, name: str, version: int) -> str:
        self._validate_name(name)
        d = os.path.join(self.history_dir, name)
        os.makedirs(d, exist_ok=True)
        return os.path.join(d, "v%d%s" % (version, CARD_SUFFIX))

    # ---------------- read ----------------
    def read_card_text(self, path: str) -> Optional[str]:
        if not os.path.isfile(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def load_concept(self, name: str) -> Optional[Concept]:
        for status in ("verified", "draft"):
            path = self.card_path(name, status)
            text = self.read_card_text(path)
            if text is not None:
                meta, body = okf.parse_frontmatter(text)
                return Concept(name, status, path, meta, body)
        return None

    def list_concepts(self, statuses: Optional[List[str]] = None) -> List[Concept]:
        statuses = statuses or ["verified", "draft"]
        out: List[Concept] = []
        for status in statuses:
            d = self.concepts_dir if status == "verified" else self.drafts_dir
            if not os.path.isdir(d):
                continue
            for fn in sorted(os.listdir(d)):
                if not fn.endswith(CARD_SUFFIX):
                    continue
                name = fn[: -len(CARD_SUFFIX)]
                text = self.read_card_text(os.path.join(d, fn))
                if text is None:
                    continue
                meta, body = okf.parse_frontmatter(text)
                out.append(Concept(name, status, os.path.join(d, fn), meta, body))
        return out

    # ---------------- write ----------------
    def write_card(self, name: str, status: str, meta: Dict[str, Any], body: str,
                   journal: bool = True, action: str = "write", detail: str = "") -> str:
        self._validate_name(name)
        errors = okf.validate_card(meta, body, status)
        if errors:
            raise ValueError("invalid knowledge card: %s" % "; ".join(errors))
        path = self.card_path(name, status)
        text = okf.build_card(meta, body)
        self._atomic_write(path, text)
        if journal:
            self.append_log(action=action, concept=name, status=status,
                            score=meta.get("score"), detail=detail)
        return path

    def snapshot_history(self, name: str, meta: Dict[str, Any], body: str) -> Optional[str]:
        version = int(meta.get("version", 1) or 1)
        if version <= 0:
            return None
        text = okf.build_card(meta, body)
        path = self.history_path(name, version)
        self._atomic_write(path, text)
        return path

    # ---------------- ledger / usage ----------------
    def read_ledger(self) -> Dict[str, Any]:
        with open(self.ledger_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write_ledger(self, data: Dict[str, Any]) -> None:
        self._atomic_write(self.ledger_path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")

    def record_feedback(self, name: str, action: str, rating: Optional[float] = None) -> Dict[str, Any]:
        ledger = self.read_ledger()
        entry = ledger["concepts"].setdefault(name, {"hits": 0, "ratings": [], "corrections": 0, "last_seen": None})
        ts = now_iso()
        if action == "hit":
            entry["hits"] = int(entry.get("hits", 0)) + 1
            entry["last_seen"] = ts
        elif action == "rate" and rating is not None:
            entry["ratings"] = entry.get("ratings", []) + [float(rating)]
            entry["last_seen"] = ts
        elif action == "correct":
            entry["corrections"] = int(entry.get("corrections", 0)) + 1
            entry["last_seen"] = ts
        ledger["feedback"].append({"ts": ts, "name": name, "action": action, "rating": rating})
        self._write_ledger(ledger)
        return {"name": name, "action": action, "entry": entry}

    def usage_signal(self, name: str) -> Tuple[float, Dict[str, Any]]:
        """(signal 0..1, detail) from ledger; neutral 0.5 when absent."""
        cfg = self.cfg
        ledger = self.read_ledger()
        entry = ledger.get("concepts", {}).get(name, {})
        if not entry:
            return float(cfg.get("scoring", {}).get("neutral_usage", 0.5)), {"absent": True}
        hits = int(entry.get("hits", 0))
        ratings = [float(r) for r in entry.get("ratings", [])]
        corrections = int(entry.get("corrections", 0))
        signal = 0.5 + 0.4 * min(1.0, hits / 10.0)
        if ratings:
            signal = 0.6 * signal + 0.4 * float(sum(ratings) / len(ratings) / 5.0)
        if corrections:
            signal = max(0.0, signal - 0.2 * corrections)
        last_seen = entry.get("last_seen")
        last_iso = last_seen or str(entry.get("created_at", ""))
        days = 0
        if last_iso:
            from .util import age_days
            d = age_days(last_iso)
            days = d if d is not None else 0
        signal *= max(0.2, 1.0 - days / 90.0)
        signal = max(0.0, min(1.0, signal))
        return signal, {"hits": hits, "ratings": ratings, "corrections": corrections, "days_since_seen": days}

    def register_ingested(self, content_hash: str, concept: str) -> None:
        ledger = self.read_ledger()
        ledger["ingested_hashes"][content_hash] = {"concept": concept, "ts": now_iso()}
        self._write_ledger(ledger)

    def is_ingested(self, content_hash: str) -> bool:
        return content_hash in self.read_ledger().get("ingested_hashes", {})

    # ---------------- log / index ----------------
    def append_log(self, action: str, concept: Optional[str] = None, status: Optional[str] = None,
                   score: Optional[float] = None, detail: str = "") -> None:
        entry = "[%s] %s" % (now_iso(), action)
        if concept:
            entry += " concept=%s" % concept
        if status:
            entry += " status=%s" % status
        if score is not None:
            entry += " score=%s" % score
        if detail:
            entry += " %s" % detail
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(entry + "\n")
        max_lines = int(self.cfg.get("logging", {}).get("log_max_lines", 5000) or 5000)
        lines = []
        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except OSError:
            pass
        if len(lines) > max_lines:
            with open(self.log_path, "w", encoding="utf-8") as f:
                f.writelines(lines[-max_lines:])

    def rebuild_index(self) -> str:
        concepts = self.list_concepts(statuses=["verified"])
        drafts = self.list_concepts(statuses=["draft"])
        lines = [
            "# Knowledge Index (OKF bundle)",
            "",
            "> Auto-generated by endlessWpKnowledgeRunner. Concept ID = file path.",
            "",
            "## Concepts (verified)",
            "",
        ]
        if concepts:
            lines += ["| name | category | score | version | description |", "|---|---|---|---|---|"]
            for c in concepts:
                lines.append("| %s | %s | %s | %s | %s |" % (
                    c.name,
                    c.category or "-",
                    ("%.0f" % c.score) if c.score is not None else "-",
                    c.meta.get("version", 1),
                    (str(c.meta.get("description", "")) or "-")[:60].replace("|", "\\|"),
                ))
        else:
            lines.append("_(none yet - run `python fw.py ingest` with a knowledge file)_")
        lines += ["", "## Drafts (below gate)", ""]
        if drafts:
            for c in drafts:
                lines.append("- `%s` (score %s)" % (c.name, ("%.0f" % c.score) if c.score is not None else "-"))
        else:
            lines.append("_(none)_")
        lines += ["", "## Sources index", ""]
        seen = set()
        for c in concepts + drafts:
            for s in okf.extract_sources(c.meta):
                p = s.get("path", "")
                if p and p not in seen:
                    seen.add(p)
                    lines.append("- `%s` <- %s" % (p, c.name))
        if not seen:
            lines.append("_(no sources recorded yet)_")
        text = "\n".join(lines) + "\n"
        self._atomic_write(self.index_path, text)
        return text

    # ---------------- livemode state ----------------
    def read_state(self) -> Dict[str, Any]:
        if os.path.isfile(self.state_path):
            with open(self.state_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"files": {}}

    def write_state(self, data: Dict[str, Any]) -> None:
        self._atomic_write(self.state_path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")
