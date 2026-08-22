# -*- coding: utf-8 -*-
"""Scoring engine: multi-signal evaluation with gate + confidence + weak points.

Signals (each 0..1):
  provenance  - OKF frontmatter valid, sources present/pinned/resolvable
  structure   - title/desc/sections/blocks/explain-words/length/not-copy
  freshness   - age & stale_after decay
  dedup       - body-hash collision with existing concepts
  verifiability - verifiable anchors (urls/fences/numbers/commands)
  jury        - optional LLM jury (mean/std across N runs), pluggable file input
  usage       - retrieval hits / ratings / corrections from ledger

Composite = 100 * sum(weight*signal) / sum(active weights).
Gate: score >= threshold -> verified. Confidence from jury deviation.
"""
import json
import os
from typing import Any, Dict, List, Optional, Tuple

from . import okf, util
from .config import Config
from .store import Store


class ScoreReport:
    def __init__(self, concept: str, score: float, gate: str,
                 signals: Dict[str, Optional[float]], jury: Dict[str, Any],
                 weak_points: List[str], confidence: float, took_ms: int,
                 detail: Dict[str, Any]):
        self.concept = concept
        self.score = score
        self.gate = gate
        self.signals = signals
        self.jury = jury
        self.weak_points = weak_points
        self.confidence = confidence
        self.took_ms = took_ms
        self.detail = detail

    def to_dict(self) -> Dict[str, Any]:
        return {
            "concept": self.concept,
            "score": round(self.score, 1),
            "gate": self.gate,
            "signals": self.signals,
            "jury": self.jury,
            "weak_points": self.weak_points,
            "confidence": round(self.confidence, 3),
            "took_ms": self.took_ms,
            "detail": self.detail,
        }


class Scorer:
    def __init__(self, cfg: Config, store: Store):
        self.cfg = cfg
        self.store = store
        self.weights = cfg.weights

    def _resolve_source_path(self, p: str):
        """Sources are repo-relative; try runner root, then repo root (parent)."""
        candidates = []
        if os.path.isabs(p):
            candidates.append(p)
        else:
            candidates.append(os.path.join(self.cfg.root, p))
            candidates.append(os.path.join(os.path.dirname(self.cfg.root), p))
        for c in candidates:
            if os.path.exists(c):
                return c
        return None

    # ---------------- per-signal calculators ----------------
    def provenance_signal(self, meta: Dict[str, Any], body: str) -> Tuple[float, List[str]]:
        reasons: List[str] = []
        fm_ok = 1.0 if (str(meta.get("schema_version", "")) or "").startswith("okf") else 0.4
        if fm_ok < 1.0:
            reasons.append("provenance: frontmatter 缺少 schema_version: okf.v1")
        sources = okf.extract_sources(meta)
        if not sources:
            reasons.append("provenance: 无 sources 溯源")
            return 0.0, reasons
        pinned = sum(1 for s in sources if s.get("pinned") or s.get("lines") or s.get("commit") or s.get("url"))
        pinned_ratio = pinned / len(sources)
        resolvable = 0
        for s in sources:
            p = s.get("path", "")
            if not p:
                continue
            if p.startswith(("http://", "https://")):
                resolvable += 1
            elif s.get("url") or s.get("commit"):
                resolvable += 1
            elif self._resolve_source_path(p) is not None:
                resolvable += 1
        resolvable_ratio = resolvable / len(sources) if sources else 0.0
        if pinned_ratio < 0.5:
            reasons.append("provenance: 过半 sources 缺少 pinned 锚点（file:line / commit / url）")
        if resolvable_ratio < 0.5:
            reasons.append("provenance: 过半 sources 当前不可解析")
        signal = 0.25 * fm_ok + 0.35 * pinned_ratio + 0.40 * resolvable_ratio
        return util.clamp(signal), reasons

    def structure_signal(self, meta: Dict[str, Any], body: str,
                         source_text: Optional[str]) -> Tuple[float, List[str]]:
        reasons: List[str] = []
        parts: List[float] = []
        parts.append(1.0 if meta.get("name") else 0.0)
        if not meta.get("name"):
            reasons.append("structure: 缺 name")
        parts.append(1.0 if meta.get("description") else 0.0)
        if not meta.get("description"):
            reasons.append("structure: 缺 description")
        sections = len([ln for ln in body.split("\n") if ln.startswith("##")]) if body else 0
        parts.append(util.clamp(sections / 2.0))
        if sections < 2:
            reasons.append("structure: 建议至少 2 个 `##` 分节")
        blocks = body.count("```") + len([ln for ln in body.split("\n") if ln.strip().startswith(("- ", "* ", "1."))])
        parts.append(util.clamp(blocks / 3.0))
        if blocks == 0:
            reasons.append("structure: 无代码块或要点列表（解释型知识建议附伪代码/要点）")
        parts.append(1.0 if util.has_explain_words(body) else 0.3)
        if not util.has_explain_words(body):
            reasons.append("structure: 缺少『为什么/适用场景』类解释词")
        length = len(body)
        lo = int(self.cfg.get("gate", {}).get("min_length", 80))
        hi = int(self.cfg.get("gate", {}).get("max_length", 65536))
        if length < lo:
            parts.append(0.2)
            reasons.append("structure: 正文过短(%d字符 < %d)" % (length, lo))
        elif length > hi:
            parts.append(0.5)
            reasons.append("structure: 正文过长，建议拆分概念")
        else:
            parts.append(1.0)
        if source_text:
            ratio = util.text_similarity(body, source_text)
            thr = float(self.cfg.get("scoring", {}).get("copy_penalty_ratio", 0.6))
            parts.append(util.clamp(1.0 - max(0.0, (ratio - thr * 0.8) / (thr * 0.8)), 0.0, 1.0))
            if ratio > thr:
                reasons.append("structure: 与来源文本相似度 %.2f > %.2f，疑似整段搬运（保留魂不搬壳）" % (ratio, thr))
        else:
            parts.append(0.8)  # no source to compare -> neutral
        return util.clamp(sum(parts) / len(parts)), reasons

    def freshness_signal(self, meta: Dict[str, Any]) -> Tuple[float, List[str]]:
        reasons: List[str] = []
        stale = meta.get("stale_after")
        ref = meta.get("updated_at") or meta.get("created_at")
        if stale:
            stale_dt = util.parse_iso(str(stale))
            if stale_dt is not None:
                from datetime import datetime
                now = datetime.now(stale_dt.tzinfo) if stale_dt.tzinfo else datetime.now()
                if now > stale_dt:
                    reasons.append("freshness: 已超过 stale_after 过期日 %s" % str(stale))
                    return 0.3, reasons
        if ref:
            days = util.age_days(str(ref))
            if days is not None:
                cap = float(self.cfg.get("scoring", {}).get("stale_after_default_days", 180))
                signal = max(0.3, 1.0 - days / cap)
                if days > cap:
                    reasons.append("freshness: 文档已 %d 天未更新（阈值 %d 天）" % (int(days), int(cap)))
                return signal, reasons
        reasons.append("freshness: 无时间戳，按中性处理")
        return 0.8, reasons

    def dedup_signal(self, name: str, body: str) -> Tuple[float, List[str]]:
        reasons: List[str] = []
        h = util.sha256_text(body)
        ledger = self.store.read_ledger()
        for other_hash, info in ledger.get("ingested_hashes", {}).items():
            if other_hash == h and info.get("concept") != name:
                reasons.append("dedup: 正文与已入库概念 %s 内容哈希一致（重复投放）" % info.get("concept"))
                return 0.3, reasons
        dupes = [c for c in self.store.list_concepts() if c.name != name and c.body == body]
        if dupes:
            reasons.append("dedup: 与 store 中 %s 正文重复" % dupes[0].name)
            return 0.2, reasons
        return 1.0, reasons

    def verifiability_signal(self, body: str) -> Tuple[float, List[str]]:
        reasons: List[str] = []
        anchors = util.count_anchors(body)
        total = anchors["urls"] * 2 + anchors["fences"] * 1.5 + anchors["commands"] * 1.5 + anchors["numbers"] * 0.5
        signal = util.clamp(total / 4.0)
        if signal < 0.4:
            reasons.append("verifiability: 验证锚点偏少（链接/代码块/指标），建议补充‘验证’小节")
        return signal, reasons

    def jury_signal(self, name: str) -> Tuple[Optional[float], Dict[str, Any]]:
        """Read pluggable jury JSON (written by any external model) and return
        (signal or None when unavailable, detail)."""
        jury_dir = os.path.join(self.store.root, "jury")
        path = os.path.join(jury_dir, name + ".json")
        if not os.path.isfile(path):
            return None, {"enabled": self.cfg.get("jury", {}).get("enabled", False), "runs": 0, "mean": None, "std": None}
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        runs = data.get("runs") or []
        if not runs:
            return None, {"enabled": True, "runs": 0, "mean": None, "std": None}
        dims = ("clarity", "faithfulness", "actionability")
        per_run: List[float] = []
        for r in runs:
            vals = [float(r.get(d, 0) or 0) for d in dims]
            per_run.append(sum(vals) / len(vals))
        mean = util.mean(per_run)
        std = util.stdev(per_run)
        signal = (mean / 10.0) * max(0.0, 1.0 - min(1.0, std / 2.5))
        return util.clamp(signal), {
            "enabled": True,
            "runs": len(runs),
            "mean": round(mean, 2),
            "std": round(std, 2),
            "signal": round(signal, 3),
        }

    # ---------------- composite ----------------
    def score_concept(self, concept: Any, source_text: Optional[str] = None,
                      include_jury: bool = True) -> ScoreReport:
        started = util.monotonic_ms()
        name = concept.name
        meta = concept.meta
        body = concept.body
        threshold = self.cfg.gate_threshold

        signals: Dict[str, Optional[float]] = {}
        weak: List[str] = []
        detail: Dict[str, Any] = {}

        s, r = self.provenance_signal(meta, body)
        signals["provenance"] = round(s, 3)
        weak.extend(r)
        s, r = self.structure_signal(meta, body, source_text)
        signals["structure"] = round(s, 3)
        weak.extend(r)
        s, r = self.freshness_signal(meta)
        signals["freshness"] = round(s, 3)
        weak.extend(r)
        s, r = self.dedup_signal(name, body)
        signals["dedup"] = round(s, 3)
        weak.extend(r)
        s, r = self.verifiability_signal(body)
        signals["verifiability"] = round(s, 3)
        weak.extend(r)
        usage_s, usage_detail = self.store.usage_signal(name)
        signals["usage"] = round(usage_s, 3)
        detail["usage"] = usage_detail

        jury_signal: Optional[float] = None
        jury_detail: Dict[str, Any] = {}
        if include_jury and self.cfg.get("jury", {}).get("enabled", False):
            jury_signal, jury_detail = self.jury_signal(name)
        signals["jury"] = round(jury_signal, 3) if jury_signal is not None else None
        if jury_detail:
            detail["jury"] = jury_detail

        active = {k: w for k, w in self.weights.items() if signals.get(k) is not None}
        total_w = sum(active.values())
        if total_w <= 0:
            score, confidence = 0.0, 0.0
        else:
            raw = sum(active[k] * float(signals[k]) for k in active) / total_w
            score = round(raw * 100.0, 1)
            confidence = 0.9 if jury_signal is None else (1.0 - min(1.0, jury_detail.get("std", 0) / 2.5))

        gate = "pass" if score >= threshold else "fail"
        if gate == "fail":
            gap = threshold - score
            weak.append("gate: score %.1f < 门禁阈值 %s（差 %.1f 分）" % (score, threshold, gap))
        return ScoreReport(
            concept=name,
            score=score,
            gate=gate,
            signals=signals,
            jury=jury_detail,
            weak_points=weak,
            confidence=confidence,
            took_ms=util.monotonic_ms() - started,
            detail=detail,
        )

    # ---------------- reliability (fragility constraint) ----------------
    def eval_repeated(self, concept: Any, n: int = 3, source_text: Optional[str] = None) -> Dict[str, Any]:
        """Repeat scoring n times, report mean/std (flywheel.md §9.1)."""
        reports = [self.score_concept(concept, source_text=source_text) for _ in range(n)]
        scores = [r.score for r in reports]
        mu = util.mean(scores)
        sigma = util.stdev(scores)
        verdicts = [r.gate for r in reports]
        return {
            "concept": concept.name,
            "runs": n,
            "mean": round(mu, 1),
            "std": round(sigma, 1),
            "min": round(min(scores), 1),
            "max": round(max(scores), 1),
            "gates": verdicts,
            "stable": sigma <= 2.0,
            "reports": [r.to_dict() for r in reports],
        }