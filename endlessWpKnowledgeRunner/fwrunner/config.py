# -*- coding: utf-8 -*-
"""Configuration: default + JSON overlay, threshold/weights, source dirs."""
import json
import os
from typing import Any, Dict, List, Optional

DEFAULTS: Dict[str, Any] = {
    "runner_root": None,          # auto: directory containing config.json
    "store_dir": "store",
    "source_dirs": ["sources"],   # liveMode scan roots (relative to runner root)
    "watch_dirs": [],             # extra dirs scanned in liveMode (e.g. ["../wiki/docs"])
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
        "dir": "store/jury",       # where external jury JSON files land
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
        "state_file": ".livemode-state.json",
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
        return os.path.join(self.root, str(self.get("store_dir", "store")))

    @property
    def gate_threshold(self) -> float:
        return float(self.data.get("gate", {}).get("threshold", 70))

    @property
    def weights(self) -> Dict[str, float]:
        return dict(self.data.get("scoring", {}).get("weights", DEFAULTS["scoring"]["weights"]))

    @property
    def source_dirs(self) -> List[str]:
        dirs: List[str] = list(self.get("source_dirs", ["sources"]))
        for d in self.get("watch_dirs", []):
            dirs.append(d)
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