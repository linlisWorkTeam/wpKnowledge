# -*- coding: utf-8 -*-
"""liveMode source scanning: find knowledge candidates not yet ingested.

The scheduler side (DSH plugin) calls `scan` to get candidates, then optionally
spawns a harvester agent per candidate; the agent's structured extraction is
handed back to `ingest` (--from-harvester). Deterministic fallback ingests the
raw file content.
"""
import json
import os
from typing import Any, Dict, List, Optional

from . import util
from .config import Config
from .store import Store

IGNORE_DIRS = {".git", ".dsh", "__pycache__", "node_modules", "dist", "build", "history", "jury", "runtime", "schema"}
IGNORE_FILES = {"index.md", "log.md", "README.md", "ledger.json"}


def scan(cfg: Config, store: Store, limit: Optional[int] = None) -> Dict[str, Any]:
    """Return candidate files (new or changed) not yet ingested."""
    cfg_limit = int(cfg.get("livemode", {}).get("max_per_cycle", 4))
    limit = limit or cfg_limit
    state = store.read_state()
    files_state: Dict[str, Any] = state.setdefault("files", {})
    candidates: List[Dict[str, Any]] = []
    for abs_dir in cfg.source_dirs:
        if not os.path.isdir(abs_dir):
            continue
        for root, dirs, fnames in os.walk(abs_dir):
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            for fn in sorted(fnames):
                if not fn.endswith(".md"):
                    continue
                if fn in IGNORE_FILES:
                    continue
                full = os.path.join(root, fn)
                rel = cfg.path_label(full)
                h = util.sha256_file(full)
                prev = files_state.get(rel) or {}
                if prev.get("hash") == h:
                    continue  # un-changed
                if store.is_ingested(h):
                    # already ingested under a concept; advance cursor
                    files_state[rel] = {"hash": h, "concept": prev.get("concept"), "ts": util.now_iso()}
                    continue
                mtime = os.path.getmtime(full)
                candidates.append({"path": rel, "full_path": full, "hash": h,
                                   "mtime": mtime, "size": os.path.getsize(full)})
    candidates.sort(key=lambda c: c["mtime"])
    store.write_state(state)  # persists cursor advances for ingested files
    return {
        "candidates": candidates[:limit],
        "total": len(candidates),
        "limit": limit,
        "note": "liveMode: %d 个候选（已按 mtime 升序）；harvester agent 逐条提炼后调用 fw_ingest" % len(candidates),
    }


def mark_handled(cfg: Config, store: Store, rel_path: str, concept: str) -> None:
    state = store.read_state()
    files = state.setdefault("files", {})
    full = cfg.resolve_repo_path(rel_path)
    files[rel_path] = {"hash": util.sha256_file(full) if os.path.isfile(full) else "",
                       "concept": concept, "ts": util.now_iso()}
    store.write_state(state)


def load_harvester_payload(path: str) -> Dict[str, Any]:
    """Read a harvester agent's structured extraction JSON (produced by the DSH
    plugin from the subagent's structured result)."""
    if not os.path.isfile(path):
        raise FileNotFoundError("harvester payload not found: %s" % path)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data
