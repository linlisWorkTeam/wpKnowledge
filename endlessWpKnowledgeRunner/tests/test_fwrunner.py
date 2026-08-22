# -*- coding: utf-8 -*-
"""Unit tests for endlessWpKnowledgeRunner (stdlib unittest, runnable with:
python -m unittest discover -s tests -v
or plain: python tests/test_fwrunner.py)
"""
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fwrunner import livemode, okf, util  # noqa: E402
from fwrunner.config import load_config  # noqa: E402
from fwrunner.ingest import Ingester  # noqa: E402
from fwrunner.retrieve import Retriever  # noqa: E402
from fwrunner.scorer import Scorer  # noqa: E402
from fwrunner.store import Store  # noqa: E402

GOOD_BODY = """## 概述

X 组件解决 Y 问题。

## 设计要点

```text
a -> b -> c
```

- 边界处理：空输入返回默认值。

## 为什么

1. 历史需求驱动；权衡：简单直接。
2. 适用场景：多协议并存时采用。

## 验证

- 文档 docs/x.md 第 1-20 行
- 复现: python -m x 压测 10000 条
"""

BAD_BODY = "随便写点没有来源也没有结构的文字。"


class RunnerTestCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="fw-test-")
        # copy the real config so defaults match
        cfg_src = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")
        shutil.copy(cfg_src, os.path.join(self.root, "config.json"))
        os.makedirs(os.path.join(self.root, "sources"), exist_ok=True)
        self.cfg = load_config(self.root)
        self.store = Store(self.cfg)
        self.scorer = Scorer(self.cfg, self.store)
        self.ing = Ingester(self.cfg, self.store, self.scorer)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)


class TestOKF(RunnerTestCase):
    def test_roundtrip_frontmatter(self):
        meta = {
            "schema_version": "okf.v1",
            "name": "x",
            "sources": [{"path": "a/b.md", "lines": "1-5", "pinned": True}],
            "tags": ["a", "b"],
            "status": "verified",
            "score": 88.5,
        }
        card = okf.build_card(meta, GOOD_BODY)
        meta2, body = okf.parse_frontmatter(card)
        self.assertEqual(body, GOOD_BODY.rstrip("\n"))
        self.assertEqual(meta2["sources"], meta["sources"])
        self.assertEqual(meta2["score"], 88.5)
        self.assertEqual(meta2["tags"], ["a", "b"])

    def test_sources_urls_not_mangled(self):
        meta, body = okf.parse_frontmatter("---\nsources:\n  - path: https://github.com/x/y\n    pinned: true\n---\n\nbody\n")
        self.assertEqual(meta["sources"], [{"path": "https://github.com/x/y", "pinned": True}])


class TestTokenize(unittest.TestCase):
    def test_mixed(self):
        toks = util.tokenize("OKF 知识格式 knowledge format")
        self.assertIn("okf", toks)
        self.assertIn("知识", toks)
        self.assertIn("格式", toks)  # bigram of 知识格式
        self.assertIn("knowledge", toks)


class TestIngestGate(RunnerTestCase):
    def test_good_passes(self):
        r = self.ing.run(content=GOOD_BODY, name="good-card", source="docs/x.md", pinned=True)
        self.assertEqual(r.gate, "pass")
        self.assertEqual(r.status, "verified")
        self.assertGreaterEqual(r.score, 70)
        card = self.store.load_concept("good-card")
        self.assertEqual(card.status, "verified")
        self.assertEqual(card.meta["verified"], True)

    def test_bad_fails_to_draft(self):
        r = self.ing.run(content=BAD_BODY, name="junk")
        self.assertEqual(r.gate, "fail")
        self.assertEqual(r.status, "draft")
        card = self.store.load_concept("junk")
        self.assertEqual(card.status, "draft")

    def test_verified_not_clobbered_by_worse_version(self):
        r1 = self.ing.run(content=GOOD_BODY, name="stable", source="docs/x.md", pinned=True)
        self.assertEqual(r1.status, "verified")
        r2 = self.ing.run(content=BAD_BODY, name="stable")
        # poor re-push must NOT clobber the verified card
        self.assertEqual(r2.status, "verified")
        self.assertEqual(r2.gate, "fail")
        self.assertIn("保留已验证版本", r2.note)
        card = self.store.load_concept("stable")
        self.assertEqual(card.status, "verified")
        self.assertGreaterEqual(card.score, 70)

    def test_version_bump_and_history(self):
        self.ing.run(content=GOOD_BODY, name="v-card", source="docs/x.md", pinned=True)
        self.ing.run(content=GOOD_BODY + "\n\n## 新增\n\n- 补充内容\n", name="v-card",
                     source="docs/x.md", pinned=True)
        card = self.store.load_concept("v-card")
        self.assertEqual(card.meta["version"], 2)
        hist = os.path.join(self.store.history_dir, "v-card", "v1.md")
        self.assertTrue(os.path.isfile(hist))


class TestScoringSignals(RunnerTestCase):
    def test_provenance_absent(self):
        r = self.ing.run(content=GOOD_BODY, name="no-src")
        self.assertLess(r.report["signals"]["provenance"], 0.5)

    def test_copy_penalty(self):
        src_file = os.path.join(self.root, "sources", "origin.md")
        with open(src_file, "w", encoding="utf-8") as f:
            f.write(GOOD_BODY)  # body is a verbatim copy of the source
        r = self.ing.run(content=GOOD_BODY, name="copied", source="sources/origin.md")
        # structure signal must be penalized (copy penalty)
        self.assertLess(r.report["signals"]["structure"], 0.9)

    def test_usage_signal_rises_with_feedback(self):
        self.ing.run(content=GOOD_BODY, name="used", source="docs/x.md", pinned=True)
        s0, _ = self.store.usage_signal("used")
        self.ing.run(content=GOOD_BODY, name="used2", source="docs/x.md", pinned=True)
        self.store.record_feedback("used2", "hit")
        self.store.record_feedback("used2", "hit")
        self.store.record_feedback("used2", "rate", rating=5.0)
        s1, _ = self.store.usage_signal("used2")
        self.assertGreater(s1, s0)

    def test_eval_repeated_stable(self):
        self.ing.run(content=GOOD_BODY, name="ev", source="docs/x.md", pinned=True)
        concept = self.store.load_concept("ev")
        out = self.scorer.eval_repeated(concept, n=3)
        self.assertEqual(out["runs"], 3)
        self.assertEqual(out["std"], 0.0)
        self.assertTrue(out["stable"])


class TestRetrieval(RunnerTestCase):
    def test_bm25_ranking(self):
        self.ing.run(content=GOOD_BODY, name="alpha", source="docs/x.md", pinned=True)
        self.ing.run(content="# 完全无关\n\n## 概述\n\n讲的是天气与交通。\n\n## 设计\n\n- 与风力和方向无关的噪音。", name="beta")
        self.cfg.data["retrieval"]["include_drafts"] = True
        r = Retriever(self.cfg, self.store)
        out = r.search("边界处理 空输入 默认值", top_k=5)
        self.assertGreaterEqual(out["total"], 2)
        self.assertEqual(out["hits"][0]["name"], "alpha")

    def test_query_records_hits(self):
        self.ing.run(content=GOOD_BODY, name="hitme", source="docs/x.md", pinned=True)
        Retriever(self.cfg, self.store).search("hitme")
        signal, detail = self.store.usage_signal("hitme")
        self.assertGreaterEqual(detail["hits"], 1)


class TestLiveMode(RunnerTestCase):
    def test_scan_finds_and_dedups(self):
        src = os.path.join(self.root, "sources", "new.md")
        with open(src, "w", encoding="utf-8") as f:
            f.write(GOOD_BODY)
        scan1 = livemode.scan(self.cfg, self.store)
        self.assertEqual(scan1["total"], 1)
        cand = scan1["candidates"][0]
        res = self.ing.run(file_path=cand["full_path"], name="scanned", source=cand["path"],
                           silent_file=cand["path"])
        self.assertEqual(res.status, "verified")
        scan2 = livemode.scan(self.cfg, self.store)
        self.assertEqual(scan2["total"], 0)  # cursor advanced

    def test_harvest_deterministic(self):
        src = os.path.join(self.root, "sources", "harvest-me.md")
        with open(src, "w", encoding="utf-8") as f:
            f.write(GOOD_BODY)
        self.ing.run(file_path=src, source="sources/harvest-me.md", name="pre")
        # second scan: content unchanged -> no candidates
        scan = livemode.scan(self.cfg, self.store)
        self.assertEqual(scan["total"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)