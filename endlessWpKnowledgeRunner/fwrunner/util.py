# -*- coding: utf-8 -*-
"""Small shared helpers: CJK-aware tokenization, text similarity, time utils."""
import hashlib
import re
import time
from datetime import datetime
from typing import Dict, Iterable, List, Optional

_CJK_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]")
_WORD_RE = re.compile(r"[a-zA-Z0-9_]+")
_URL_RE = re.compile(r"https?://\S+")
_CODE_FENCE_RE = re.compile(r"```|~~~")
_NUM_RE = re.compile(r"\d+(\.\d+)?\s*%?")
_CMD_RE = re.compile(r"^\s*(\$|>)\s*[\w./-]", re.MULTILINE)
_EXPLAIN_WORDS = [
    "为什么", "原因", "设计", "权衡", "适用场景", "解决", "思路",
    "why", "reason", "trade-off", "design", "scenario", "when to use",
]


def tokenize(text: str) -> List[str]:
    """Tokenize mixed CJK / Latin text.

    CJK text is split into unigrams plus bigrams so a plain BM25 can match
    Chinese queries; Latin text is split on word boundaries; digits kept.
    """
    text = (text or "").lower()
    tokens: List[str] = []
    seen: Dict[str, int] = {}
    cjk_chars = _CJK_RE.findall(text)
    # contiguous CJK runs -> unigram + bigram
    runs = re.findall(r"[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]+", text)
    for run in runs:
        chars = list(run)
        for ch in chars:
            tokens.append(ch)
        for i in range(len(chars) - 1):
            tokens.append(chars[i] + chars[i + 1])
    if cjk_chars:
        # strip CJK before latin tokenization to avoid mixed junk tokens
        text = _CJK_RE.sub(" ", text)
    for w in _WORD_RE.findall(text):
        tokens.append(w)
    # cheap frequency dedup inside one document (list of tf)
    out: List[str] = []
    for t in tokens:
        if t in seen:
            continue
        seen[t] = 1
        out.append(t)
    return out


def text_similarity(a: str, b: str) -> float:
    """Normalized text similarity in [0, 1] (sequence-based, cheap)."""
    import difflib
    if not a or not b:
        return 0.0
    a = re.sub(r"\s+", " ", (a or "").strip())
    b = re.sub(r"\s+", " ", (b or "").strip())
    if not a or not b:
        return 0.0
    if len(a) < 10 or len(b) < 10:
        return 1.0 if a == b else 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def sha256_text(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def age_days(value: Optional[str], ref: Optional[datetime] = None) -> Optional[float]:
    """Days between a datetime string and now (or ref). None when unparsable."""
    dt = parse_iso(value)
    if dt is None:
        return None
    base = ref or datetime.now(dt.tzinfo) if dt.tzinfo else (ref or datetime.now())
    if dt.tzinfo is None and base.tzinfo is not None:
        dt = dt.replace(tzinfo=base.tzinfo)
    return max(0.0, (base - dt).total_seconds() / 86400.0)


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def mean(values: Iterable[float]) -> float:
    vals = list(values)
    return sum(vals) / len(vals) if vals else 0.0


def stdev(values: Iterable[float]) -> float:
    vals = list(values)
    if len(vals) < 2:
        return 0.0
    m = mean(vals)
    return (sum((v - m) ** 2 for v in vals) / (len(vals) - 1)) ** 0.5


def count_anchors(text: str) -> Dict[str, int]:
    """Count 'verifiable anchors' in a body: URLs, code fences, numbers, commands."""
    return {
        "urls": len(_URL_RE.findall(text or "")),
        "fences": len(_CODE_FENCE_RE.findall(text or "")),
        "numbers": len(_NUM_RE.findall(text or "")),
        "commands": len(_CMD_RE.findall(text or "")),
    }


def has_explain_words(text: str) -> bool:
    low = (text or "").lower()
    return any(w in low for w in _EXPLAIN_WORDS)


def slugify(name: str) -> str:
    """Build a safe concept id from arbitrary text (CJK allowed via hash fallback)."""
    name = (name or "").strip().lower()
    # Replace CJK runs with a stable hash fragment so ids stay path-safe.
    name = re.sub(r"[\u4e00-\u9fff]+", lambda m: "z" + str(abs(hash(m.group(0))) % 1000000), name)
    name = re.sub(r"[^a-z0-9_\-.\u4e00-\u9fff]+", "-", name)
    name = re.sub(r"-{2,}", "-", name).strip("-")
    return (name or "concept")[:120]


def monotonic_ms() -> int:
    return int(time.monotonic() * 1000)