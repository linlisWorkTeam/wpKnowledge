#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Local dashboard server for endlessWpKnowledgeRunner."""
import argparse
import json
import mimetypes
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlsplit

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from fwrunner import livemode  # noqa: E402
from fwrunner.config import load_config  # noqa: E402
from fwrunner.ingest import score_one  # noqa: E402
from fwrunner.retrieve import Retriever  # noqa: E402
from fwrunner.scorer import Scorer  # noqa: E402
from fwrunner.store import Store  # noqa: E402


def make_context(root):
    cfg = load_config(root)
    store = Store(cfg)
    return cfg, store, Scorer(cfg, store), Retriever(cfg, store)


def relative_path(root, path):
    try:
        return os.path.relpath(path, root).replace("\\", "/")
    except ValueError:
        return path


def card_summary(root, card):
    data = card.to_dict(include_body=False)
    data["path"] = relative_path(root, card.path)
    breakdown = card.meta.get("score_breakdown")
    if not isinstance(breakdown, dict):
        # Older cards were written with a YAML mapping that the pragmatic
        # parser exposed as top-level signal keys. Keep the dashboard useful
        # without rewriting those existing cards.
        signal_keys = ("provenance", "structure", "freshness", "dedup", "verifiability", "jury", "usage")
        breakdown = {key: card.meta[key] for key in signal_keys if key in card.meta}
    data["score_breakdown"] = breakdown
    data["confidence"] = card.meta.get("confidence")
    return data


def status_payload(store):
    concepts = store.list_concepts()
    scores = [c.score for c in concepts if c.score is not None]
    ledger = store.read_ledger()
    try:
        with open(store.log_path, "r", encoding="utf-8") as fh:
            latest_log = fh.read().splitlines()[-5:]
    except OSError:
        latest_log = []
    return {
        "ok": True,
        "concepts_total": len(concepts),
        "verified": sum(c.status == "verified" for c in concepts),
        "drafts": sum(c.status == "draft" for c in concepts),
        "avg_score": round(sum(scores) / len(scores), 1) if scores else None,
        "min_score": min(scores) if scores else None,
        "max_score": max(scores) if scores else None,
        "ingested_hashes": len(ledger.get("ingested_hashes", {})),
        "feedback_events": len(ledger.get("feedback", [])),
        "latest_log": latest_log,
    }


class DashboardHandler(BaseHTTPRequestHandler):
    server_version = "WpKnowledgeDashboard/0.1"

    @property
    def root(self):
        return self.server.runner_root

    def _send(self, status, body, content_type="application/json; charset=utf-8"):
        if isinstance(body, (dict, list)):
            raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
        elif isinstance(body, str):
            raw = body.encode("utf-8")
        else:
            raw = bytes(body)
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def _error(self, status, message):
        self._send(status, {"ok": False, "error": message})

    def _context(self):
        return make_context(self.root)

    def do_GET(self):  # noqa: N802
        parsed = urlsplit(self.path)
        try:
            if parsed.path in ("/", "/dashboard.html"):
                return self._serve("dashboard.html")
            if parsed.path in ("/app.js", "/styles.css"):
                return self._serve(parsed.path.lstrip("/"))
            if parsed.path == "/favicon.ico":
                return self._send(204, b"", "image/x-icon")
            if parsed.path == "/api/status":
                _, store, _, _ = self._context()
                return self._send(200, status_payload(store))
            if parsed.path == "/api/concepts":
                _, store, _, _ = self._context()
                status = parse_qs(parsed.query).get("status", [None])[0]
                statuses = [status] if status in ("verified", "draft") else ["verified", "draft"]
                cards = [card_summary(self.root, c) for c in store.list_concepts(statuses)]
                cards.sort(key=lambda c: (0 if c["status"] == "verified" else 1, -(float(c.get("score") or 0))))
                return self._send(200, {"ok": True, "concepts": cards})
            if parsed.path == "/api/query":
                _, _, _, retriever = self._context()
                query = parse_qs(parsed.query)
                q = query.get("q", [""])[0]
                top = int(query.get("top", [8])[0])
                return self._send(200, retriever.search(
                    q, top_k=max(1, min(top, 50)),
                    status=query.get("status", [None])[0],
                    category=query.get("category", [None])[0],
                    platform=query.get("platform", [None])[0],
                    record_feedback=False,
                ))
            if parsed.path == "/api/scan":
                cfg, store, _, _ = self._context()
                return self._send(200, livemode.scan(cfg, store))
            if parsed.path.startswith("/api/concepts/"):
                name = unquote(parsed.path[len("/api/concepts/"):])
                _, store, _, _ = self._context()
                card = store.load_concept(name)
                if card is None:
                    return self._error(404, "concept not found: %s" % name)
                data = card_summary(self.root, card)
                data["body"] = card.body
                return self._send(200, {"ok": True, "concept": data})
            return self._error(404, "not found")
        except Exception as exc:  # noqa: BLE001
            return self._error(500, "%s: %s" % (type(exc).__name__, exc))

    def do_POST(self):  # noqa: N802
        parsed = urlsplit(self.path)
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
            if parsed.path == "/api/feedback":
                name = str(payload.get("name", "")).strip()
                action = str(payload.get("action", "")).strip()
                if not name or action not in ("hit", "rate", "correct"):
                    return self._error(400, "name and action(hit|rate|correct) are required")
                _, store, _, _ = self._context()
                rating = payload.get("rating")
                if action == "rate":
                    if rating is None or not 0 <= float(rating) <= 5:
                        return self._error(400, "rating must be between 0 and 5")
                    rating = float(rating)
                return self._send(200, {"ok": True, "feedback": store.record_feedback(name, action, rating)})
            if parsed.path == "/api/rescore":
                name = str(payload.get("name", "")).strip()
                if not name:
                    return self._error(400, "name is required")
                cfg, store, scorer, _ = self._context()
                return self._send(200, {"ok": True, "report": score_one(cfg, store, scorer, name)})
            return self._error(404, "not found")
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            return self._error(400, "invalid JSON: %s" % exc)
        except Exception as exc:  # noqa: BLE001
            return self._error(500, "%s: %s" % (type(exc).__name__, exc))

    def _serve(self, filename):
        if filename not in {"dashboard.html", "app.js", "styles.css"}:
            return self._error(404, "asset not found")
        path = os.path.join(os.path.dirname(__file__), filename)
        if not os.path.isfile(path):
            return self._error(404, "asset not found")
        with open(path, "rb") as fh:
            raw = fh.read()
        content_type = mimetypes.guess_type(path)[0] or "application/octet-stream"
        return self._send(200, raw, content_type + "; charset=utf-8")

    def log_message(self, fmt, *args):
        sys.stderr.write("[dashboard] " + (fmt % args) + "\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Local wpKnowledge dashboard")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4174)
    parser.add_argument("--root", default=ROOT, help="runner root")
    args = parser.parse_args(argv)
    server = ThreadingHTTPServer((args.host, args.port), DashboardHandler)
    server.runner_root = os.path.abspath(args.root)
    print("wpKnowledge dashboard: http://%s:%d" % (args.host, args.port))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
