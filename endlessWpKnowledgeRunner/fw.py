#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""endlessWpKnowledgeRunner CLI.

Zero-dependency knowledge flywheel runner: OKF consolidation, multi-signal
scoring, BM25 retrieval, liveMode scanning. Every command prints JSON when
--json is passed (the DSH plugin consumes this).

Usage:
  python fw.py init
  python fw.py ingest --file <path> [--name n] [--source s] [--category c] [--tags a,b] [--force-draft]
  python fw.py ingest --content "..." --name n --source s
  python fw.py score --name <concept> | --all
  python fw.py eval --name <concept> --runs 3
  python fw.py query --q "鍏抽敭璇? [--top 5] [--status verified|draft] [--category c]
  python fw.py get --name <concept>
  python fw.py status
  python fw.py scan
  python fw.py harvest            # deterministic liveMode cycle (no agents)
  python fw.py feedback --name n --action hit|rate|correct [--rating 4]
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fwrunner.config import load_config  # noqa: E402
from fwrunner.ingest import Ingester, score_all, score_one  # noqa: E402
from fwrunner.retrieve import Retriever  # noqa: E402
from fwrunner.scorer import Scorer  # noqa: E402
from fwrunner.store import Store  # noqa: E402
from fwrunner import livemode  # noqa: E402


def _json_out(data, pretty: bool) -> None:
    if pretty:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(data, ensure_ascii=False))


def _error(msg: str) -> None:
    sys.stderr.write("fw error: %s\n" % msg)
    sys.exit(1)


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(prog="fw", description="endlessWpKnowledgeRunner")
    parser.add_argument("--root", default=None, help="runner root (default: this file's dir)")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", help="machine-readable JSON output")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init", parents=[common], help="ensure store layout exists")
    p_ing = sub.add_parser("ingest", parents=[common], help="trigger: push knowledge into the flywheel")
    p_ing.add_argument("--file", default=None)
    p_ing.add_argument("--content", default=None)
    p_ing.add_argument("--name", default=None)
    p_ing.add_argument("--title", default=None)
    p_ing.add_argument("--description", default=None)
    p_ing.add_argument("--category", default=None)
    p_ing.add_argument("--tags", default=None)
    p_ing.add_argument("--source", default=None)
    p_ing.add_argument("--source-lines", dest="source_lines", default=None)
    p_ing.add_argument("--force-draft", action="store_true")
    p_ing.add_argument("--pinned", action="store_true")
    p_ing.add_argument("--silent-file", default=None, help="mark this source path as handled in liveMode state")

    p_sc = sub.add_parser("score", parents=[common], help="evaluate one or all concepts")
    p_sc.add_argument("--name", default=None)
    p_sc.add_argument("--all", action="store_true")
    p_sc.add_argument("--status", default=None)

    p_ev = sub.add_parser("eval", parents=[common], help="repeated scoring: mean/std (fragility constraint)")
    p_ev.add_argument("--name", default=None)
    p_ev.add_argument("--all", action="store_true")
    p_ev.add_argument("--runs", type=int, default=3)

    p_q = sub.add_parser("query", parents=[common], help="apply: retrieve knowledge")
    p_q.add_argument("--q", default="")
    p_q.add_argument("--top", type=int, default=None)
    p_q.add_argument("--status", default=None)
    p_q.add_argument("--category", default=None)
    p_q.add_argument("--platform", default=None)
    p_q.add_argument("--no-feedback", action="store_true", help="read-only: 不记录命中反馈（HTTP 外部调用默认）")

    p_get = sub.add_parser("get", parents=[common], help="fetch one concept card")
    p_get.add_argument("--name", required=True)

    sub.add_parser("status", parents=[common], help="flywheel dashboard")
    sub.add_parser("scan", parents=[common], help="liveMode: list un-ingested candidates")
    sub.add_parser("harvest", parents=[common], help="liveMode deterministic cycle: ingest raw candidates")

    p_fb = sub.add_parser("feedback", parents=[common], help="record usage feedback (usage signal)")
    p_fb.add_argument("--name", required=True)
    p_fb.add_argument("--action", required=True, choices=["hit", "rate", "correct"])
    p_fb.add_argument("--rating", type=float, default=None)

    args = parser.parse_args(argv)
    cfg = load_config(args.root)
    try:
        store = Store(cfg)
        scorer = Scorer(cfg, store)
        if args.cmd == "init":
            _json_out({"ok": True, "store": store.root}, args.json)
            return
        if args.cmd == "ingest":
            content = args.content
            if content is None and not sys.stdin.isatty() and args.file is None:
                content = sys.stdin.read()
            tags = [t.strip() for t in (args.tags or "").split(",") if t.strip()] or None
            ing = Ingester(cfg, store, scorer)
            result = ing.run(
                content=content, file_path=args.file, name=args.name, title=args.title,
                description=args.description, category=args.category, tags=tags,
                source=args.source, force_draft=args.force_draft, pinned=args.pinned,
                silent_file=args.silent_file, source_lines=args.source_lines,
            )
            _json_out(result.to_dict(), args.json)
            return
        if args.cmd == "score":
            if args.name:
                _json_out(score_one(cfg, store, scorer, args.name), args.json)
            elif args.all:
                _json_out(score_all(cfg, store, scorer, statuses=[args.status] if args.status else None), args.json)
            else:
                _error("score needs --name or --all")
            return
        if args.cmd == "eval":
            concepts = store.list_concepts()
            if args.name:
                concepts = [c for c in concepts if c.name == args.name]
            if not concepts:
                _error("no concepts to eval")
            out = []
            for c in concepts[:20]:
                out.append(scorer.eval_repeated(c, n=max(1, args.runs)))
            _json_out(out, args.json)
            return
        if args.cmd == "query":
            r = Retriever(cfg, store)
            _json_out(r.search(args.q, top_k=args.top, status=args.status,
                               category=args.category, platform=args.platform,
                               record_feedback=not args.no_feedback), args.json)
            return
        if args.cmd == "get":
            r = Retriever(cfg, store)
            hit = r.get(args.name)
            if hit is None:
                _error("concept not found: %s" % args.name)
            _json_out(hit, args.json)
            return
        if args.cmd == "status":
            concepts = store.list_concepts()
            verified = [c for c in concepts if c.status == "verified"]
            drafts = [c for c in concepts if c.status == "draft"]
            scores = [c.score for c in concepts if c.score is not None]
            ledger = store.read_ledger()
            _json_out({
                "ok": True,
                "concepts_total": len(concepts),
                "verified": len(verified),
                "drafts": len(drafts),
                "avg_score": round(sum(scores) / len(scores), 1) if scores else None,
                "min_score": min(scores) if scores else None,
                "max_score": max(scores) if scores else None,
                "ingested_hashes": len(ledger.get("ingested_hashes", {})),
                "feedback_events": len(ledger.get("feedback", [])),
                "latest_log": _tail(store.log_path, 5),
                "store": store.root,
            }, args.json)
            return
        if args.cmd == "scan":
            _json_out(livemode.scan(cfg, store), args.json)
            return
        if args.cmd == "harvest":
            scan_result = livemode.scan(cfg, store)
            ing = Ingester(cfg, store, scorer)
            results = []
            for cand in scan_result["candidates"]:
                try:
                    res = ing.run(file_path=cand["full_path"], name=None,
                                  source=cand["path"], silent_file=cand["path"])
                    results.append(res.to_dict())
                except Exception as exc:  # noqa: BLE001
                    results.append({"path": cand["path"], "error": str(exc)})
            _json_out({"scan": scan_result, "ingested": results}, args.json)
            return
        if args.cmd == "feedback":
            _json_out(store.record_feedback(args.name, args.action, rating=args.rating), args.json)
            return
        _error("unknown command: %s" % args.cmd)
    except Exception as exc:  # noqa: BLE001
        _error("%s: %s" % (type(exc).__name__, exc))


def _tail(path: str, n: int) -> list:
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
        return lines[-n:]
    except OSError:
        return []


if __name__ == "__main__":
    main()
