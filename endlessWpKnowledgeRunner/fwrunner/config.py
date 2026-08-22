# -*- coding: utf-8 -*-
"""Configuration: runner code paths, knowledge-base paths and gate settings."""
import json
import os
from typing import Any, Dict, List, Optional

DEFAULTS: Dict[str, Any] = {
    "runner_root": None,          # auto: directory containing config.json
    # The runner is code; the knowledge base is a sibling directory.  Keep
    # store_dir as a legacy alias for installations that still use the old
    # runner-local layout.
    "knowledge_dir": "../knowledge",
    "store_dir": "store",
    "source_dirs": ["inbox"],      # roots relative to knowledge_dir
    "watch_dirs": [],              # extra roots relative to runner root
    "gate": {
        "threshold": 70,          # score >= threshold -> verified
        "min_length": 80,         # body chars below -> structure penalty
        "max_length": 65536,
    },
    "scoring": {
        "weights": {
            "provenance": 0.25,
            "structure": 0.20,
            "freshness": 0.10,
            "dedup": 0.10,
            "verifiability": 0.05,
            "jury": 0.20,          # disabled -> weight redistributed
            "usage": 0.10,
        },
        "stale_after_default_days": 180,
        "copy_penalty_ratio": 0.60,   # body-vs-source similarity above -> penalty
        "neutral_usage": 0.5,
    },
    "jury": {
        "enabled": False,          # LLM jury is pluggable & opt-in (see docs)
        "runs": 3,                 # repeat runs -> mean/std (fragility constraint)
        "dir": "jury",             # relative to knowledge_dir
    },
    "retrieval": {
        "top_k": 8,
        "include_drafts": False,
        "quality_weight": 0.15,    # ranking = bm25*(1-qw) + score*qw
        "k1": 1.5,
        "b": 0.75,
    },
    "livemode": {
        "interval_minutes": 15,    # used by the DSH plugin interval
        "max_per_cycle": 4,        # candidates extracted per agent cycle
        "state_file": "runtime/livemode-state.json",
    },
    "logging": {"log_max_lines": 5000},
}


class Config:
    def __init__(self, runner_root: str, data: Dict[str, Any]):
        self.root = runner_root
        self.data = data

    def __getitem__(self, key: str) -> Any:
        return self.data[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    @property
    def store_dir(self) -> str:
        return self.knowledge_dir

    @property
    def knowledge_dir(self) -> str:
        configured = self.get("knowledge_dir")
        if configured:
            return configured if os.path.isabs(configured) else os.path.normpath(os.path.join(self.root, configured))
        legacy = str(self.get("store_dir", "store"))
        return legacy if os.path.isabs(legacy) else os.path.normpath(os.path.join(self.root, legacy))

    @property
    def repo_root(self) -> str:
        return os.path.dirname(self.root)

    def resolve_source_dir(self, path: str) -> str:
        """Resolve a managed inbox path or an explicitly configured watch path."""
        return path if os.path.isabs(path) else os.path.normpath(os.path.join(self.knowledge_dir, path))

    def resolve_repo_path(self, path: str) -> str:
        """Resolve a provenance/state path relative to the repository root."""
        return path if os.path.isabs(path) else os.path.normpath(os.path.join(self.repo_root, path))

    def path_label(self, path: str) -> str:
        """Return a stable repository-relative label for provenance/state."""
        return os.path.relpath(path, self.repo_root).replace("\\", "/")

    @property
    def gate_threshold(self) -> float:
        return float(self.data.get("gate", {}).get("threshold", 70))

    @property
    def weights(self) -> Dict[str, float]:
        return dict(self.data.get("scoring", {}).get("weights", DEFAULTS["scoring"]["weights"]))

    @property
    def source_dirs(self) -> List[str]:
        dirs: List[str] = [self.resolve_source_dir(d) for d in self.get("source_dirs", ["inbox"])]
        # watch_dirs are intentionally runner/repository paths, not writable
        # knowledge paths. They are read-only acquisition sources.
        for d in self.get("watch_dirs", []):
            dirs.append(d if os.path.isabs(d) else os.path.normpath(os.path.join(self.root, d)))
        return dirs


def _deep_merge(base: Dict[str, Any], overlay: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(base)
    for k, v in overlay.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config(runner_root: Optional[str] = None) -> Config:
    """Load config.json from runner root (default: this file's parent dir)."""
    if runner_root is None:
        runner_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data = json.loads(json.dumps(DEFAULTS))  # deep copy via JSON round-trip
    cfg_path = os.path.join(runner_root, "config.json")
    if os.path.isfile(cfg_path):
        with open(cfg_path, "r", encoding="utf-8") as f:
            data = _deep_merge(data, json.load(f))
    data["runner_root"] = runner_root
    return Config(runner_root, data)
