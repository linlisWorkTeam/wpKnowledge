# -*- coding: utf-8 -*-
"""Retrieval (Apply phase): BM25 index + frontmatter filters + quality re-rank.

Deterministic, dependency-free: CJK-aware BM25 over the OKF bundle. Ranking =
bm25 (normalized) with a quality bonus, so verified+high-scored cards surface
first. The store stays the single source of truth; feedback flows out through
the ledger (record hit), so usage becomes a scoring signal.
"""
import math
import os
from typing import Any, Dict, List, Optional

from . import okf, util
from .config import Config
from .store import Concept, Store

FIELD_BOOST = {"name": 3.0, "title": 3.0, "description": 2.0, "tags": 2.0, "body": 1.0}


class Doc:
    def __init__(self, concept: Concept, tokens: Dict[str, int], length: int):
        self.concept = concept
        self.tokens = tokens
        self.length = length


class Retriever:
    def __init__(self, cfg: Config, store: Store):
        self.cfg = cfg
        self.store = store

    def _index_doc(self, c: Concept) -> Doc:
        tokens: Dict[str, int] = {}
        def add(text: str, boost: float) -> None:
            for t in util.tokenize(text):
                tokens[t] = tokens.get(t, 0) + boost
        add(c.name, FIELD_BOOST["name"])
        add(str(c.meta.get("title", "")), FIELD_BOOST["title"])
        add(str(c.meta.get("description", "")), FIELD_BOOST["description"])
        add(" ".join(str(x) for x in c.meta.get("tags", [])), FIELD_BOOST["tags"])
        add(c.body, FIELD_BOOST["body"])
        return Doc(c, tokens, sum(tokens.values()))

    def search(self, query: str, top_k: Optional[int] = None,
               status: Optional[str] = None, category: Optional[str] = None,
               platform: Optional[str] = None,
               record_feedback: bool = True) -> Dict[str, Any]:
        rcfg = self.cfg.get("retrieval", {})
        top_k = top_k or int(rcfg.get("top_k", 8))
        include_drafts = bool(rcfg.get("include_drafts", False))
        statuses = ["verified"] + (["draft"] if include_drafts else [])
        if status:
            statuses = [status]
        concepts = self.store.list_concepts(statuses=statuses)
        docs = [self._index_doc(c) for c in concepts]
        if category:
            docs = [d for d in docs if d.concept.category == category]
        if platform:
            docs = [d for d in docs if str(platform) in [str(p) for p in d.concept.meta.get("platforms", [])]]

        if not docs:
            return {"query": query, "hits": [], "total": 0, "suggestion": "知识库为空或条件无匹配：先用 fw_ingest 沉淀知识再检索"}

        if not query.strip():
            # no query -> list by score
            ranked = sorted(docs, key=lambda d: d.concept.score or 0, reverse=True)[:top_k]
            return {"query": "", "hits": [self._hit(d) for d in ranked], "total": len(docs)}

        q_tokens = util.tokenize(query)
        q_tf: Dict[str, int] = {}
        for t in q_tokens:
            q_tf[t] = q_tf.get(t, 0) + 1
        n = len(docs)
        avgdl = sum(d.length for d in docs) / n if n else 1.0
        k1 = float(rcfg.get("k1", 1.5))
        b = float(rcfg.get("b", 0.75))
        df: Dict[str, int] = {}
        for d in docs:
            for t in set(d.tokens):
                df[t] = df.get(t, 0) + 1

        def idf(t: str) -> float:
            f = df.get(t, 0)
            return math.log(1.0 + (n - f + 0.5) / (f + 0.5)) if f else 0.0

        results: List[Dict[str, Any]] = []
        for d in docs:
            score = 0.0
            for t, tf_q in q_tf.items():
                tf = d.tokens.get(t, 0)
                if tf == 0:
                    continue
                denom = tf + k1 * (1 - b + b * d.length / avgdl)
                score += idf(t) * (tf * (k1 + 1)) / denom * (0.5 + 0.5 * tf_q)
            results.append((score, d))

        results.sort(key=lambda pair: pair[0], reverse=True)
        max_score = results[0][0] if results else 1.0
        qw = float(rcfg.get("quality_weight", 0.15))
        out = []
        for score, d in results[:top_k]:
            norm = score / max_score if max_score > 0 else 0.0
            quality = (d.concept.score or 0) / 100.0 if d.concept.score is not None else 0.5
            rank = norm * (1 - qw) + quality * qw
            hit = self._hit(d)
            hit["relevance"] = round(rank, 4)
            hit["bm25"] = round(norm, 4)
            out.append(hit)
        out.sort(key=lambda h: h["relevance"], reverse=True)
        if record_feedback:
            for h in out:
                self.store.record_feedback(h["name"], "hit")
        return {"query": query, "hits": out, "total": len(results)}

    def _hit(self, d: Doc) -> Dict[str, Any]:
        c = d.concept
        snippet = (c.body or "").strip().replace("\n", " ")[:220]
        return {
            "name": c.name,
            "status": c.status,
            "score": c.score,
            "version": c.meta.get("version", 1),
            "category": c.category,
            "description": c.meta.get("description", ""),
            "tags": c.meta.get("tags", []),
            "sources": okf.extract_sources(c.meta),
            "path": c.path,
            "snippet": snippet,
        }

    def get(self, name: str) -> Optional[Dict[str, Any]]:
        c = self.store.load_concept(name)
        if c is None:
            return None
        self.store.record_feedback(name, "hit")
        return self._hit(Doc(c, {}, 0))