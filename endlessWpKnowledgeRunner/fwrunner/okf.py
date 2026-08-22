# -*- coding: utf-8 -*-
"""OKF knowledge cards: YAML-frontmatter subset parser/emitter + sources handling.

Aligns with okf.v1 (GoogleCloudPlatform/knowledge-catalog) and cannbot-knowledge:
Markdown body + YAML frontmatter with `sources` / `status` / `verified` as
first-class trust fields. Only a pragmatic YAML subset is parsed (flat scalars,
inline lists, block lists of scalars, block lists of mappings) - enough for
knowledge cards without any third-party dependency.
"""
import re
from typing import Any, Dict, List, Optional, Tuple

FM_RE = re.compile(r"^---\s*$")
# a "key: value" header: colon followed by whitespace, or a bare "key:" line
HEADER_RE = re.compile(r"^([A-Za-z0-9_\-]+)\s*:\s+(.*)$|^([A-Za-z0-9_\-]+):\s*$")
LIST_ITEM_RE = re.compile(r"^(\s*)-(\s+)?(.*)$")
MAP_ENTRY_RE = re.compile(r"^(\s*)([A-Za-z0-9_\-]+)\s*:\s*(.*)$|^(\s*)([A-Za-z0-9_\-]+):\s*$")


def _parse_scalar(raw: str) -> Any:
    raw = raw.strip()
    if raw == "" or raw == "null" or raw == "~":
        return None
    if len(raw) >= 2 and raw[0] in "\"'" and raw[-1] == raw[0]:
        return raw[1:-1]
    low = raw.lower()
    if low in ("true", "yes"):
        return True
    if low in ("false", "no"):
        return False
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        pass
    if " #" in raw:
        raw = raw.split(" #", 1)[0].strip()
    return raw


def _parse_inline_list(raw: str) -> List[Any]:
    raw = raw.strip()
    items: List[Any] = []
    if raw.startswith("[") and raw.endswith("]"):
        raw = raw[1:-1]
    if raw == "":
        return items
    for part in raw.split(","):
        part = part.strip()
        if part == "":
            continue
        if len(part) >= 2 and part[0] in "\"'" and part[-1] == part[0]:
            items.append(part[1:-1])
        else:
            items.append(_parse_scalar(part))
    return items


def _header_key(line: str) -> Optional[str]:
    """Return the header key when a line is 'key: value' or bare 'key:'."""
    m = HEADER_RE.match(line)
    if not m:
        return None
    return m.group(1) if m.group(1) is not None else m.group(3)


def _header_value(line: str) -> Tuple[Optional[str], str]:
    """Split a header line into (key, raw value); (None, line) when not a header.
    Leading indentation is tolerated so nested map entries parse as headers."""
    m = HEADER_RE.match(line.strip())
    if not m:
        return None, line
    if m.group(1) is not None:
        return m.group(1), (m.group(2) or "").strip()
    return m.group(3), ""


def parse_frontmatter(text: str) -> Tuple[Dict[str, Any], str]:
    """Split a card into (frontmatter dict, markdown body)."""
    lines = text.split("\n")
    meta: Dict[str, Any] = {}
    body_start = 0
    if not lines or not FM_RE.match(lines[0]):
        return meta, text
    i = 1
    cur_list_key: Optional[str] = None
    cur_list: List[Any] = []
    cur_map: Optional[Dict[str, Any]] = None
    while i < len(lines):
        line = lines[i]
        if FM_RE.match(line):
            body_start = i + 1
            break
        stripped = line.strip()
        if stripped == "" or stripped.startswith("#"):
            i += 1
            continue
        m = LIST_ITEM_RE.match(line)
        if m and cur_list_key is not None:
            rest = m.group(3).strip()
            if _header_key(rest) is not None:
                key, value = _header_value(rest)
                if cur_map is None:
                    cur_map = {}
                    cur_list.append(cur_map)
                cur_map[key] = _parse_scalar(value) if key is not None else None
            else:
                cur_list.append(_parse_scalar(rest))
                cur_map = None
            i += 1
            continue
        key, raw = _header_value(line)
        if key is None:
            # unknown line inside a block list -> scalar continuation
            if cur_list_key is not None:
                cur_list.append(_parse_scalar(stripped))
            i += 1
            continue
        if cur_list_key is not None:
            # indented map entry belonging to the current list item's map
            if line.startswith((" ", "\t")) and cur_map is not None:
                cur_map[key] = _parse_scalar(raw)
                i += 1
                continue
            meta[cur_list_key] = cur_list
            cur_list_key = None
            cur_list = []
            cur_map = None
        if raw == "":
            peek = lines[i + 1].strip() if i + 1 < len(lines) else ""
            if peek.startswith("-"):
                cur_list_key = key
                cur_list = []
                cur_map = None
                i += 1
                continue
            if peek.startswith("|"):
                i += 2
                block: List[str] = []
                while i < len(lines):
                    if FM_RE.match(lines[i]):
                        break
                    if _header_key(lines[i].strip()) is not None and not lines[i].startswith(("  ", "\t")):
                        break
                    block.append(lines[i])
                    i += 1
                meta[key] = "\n".join(block).strip("\n")
                continue
            meta[key] = None
        elif raw.startswith("[") or ("," in raw and "http" not in raw):
            meta[key] = _parse_inline_list(raw)
        else:
            meta[key] = _parse_scalar(raw)
        i += 1
    if cur_list_key is not None:
        meta[cur_list_key] = cur_list
    body = "\n".join(lines[body_start:]).strip("\n")
    return meta, body


def _fmt_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, (int, float)):
        return str(value)
    s = str(value)
    if "\n" in s:
        return "|\n" + "\n".join("  " + ln for ln in s.split("\n"))
    needs_quote = (s.startswith(("[", "{", "*", "&", "!", "%", "@", "`", "-")) or
                   any(ch in s for ch in ":,#") or s == "" or s != s.strip())
    if needs_quote:
        s = '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return s


def build_frontmatter(meta: Dict[str, Any]) -> str:
    """Emit a card frontmatter block (YAML subset)."""
    lines = ["---"]
    for key, value in meta.items():
        if value is None:
            lines.append("%s:" % key)
            continue
        if isinstance(value, list):
            flat = all(not isinstance(v, (dict, list)) for v in value)
            if flat:
                lines.append("%s: [%s]" % (key, ", ".join(_fmt_scalar(v) for v in value)))
            else:
                lines.append("%s:" % key)
                for v in value:
                    if isinstance(v, dict):
                        keys = list(v.keys())
                        if not keys:
                            lines.append("  -")
                            continue
                        first = keys[0]
                        lines.append("  - %s: %s" % (first, _fmt_scalar(v[first])))
                        for k in keys[1:]:
                            lines.append("    %s: %s" % (k, _fmt_scalar(v[k])))
                    else:
                        lines.append("  - %s" % _fmt_scalar(v))
            continue
        if isinstance(value, dict):
            lines.append("%s:" % key)
            for k, v in value.items():
                lines.append("  %s: %s" % (k, _fmt_scalar(v)))
            continue
        lines.append("%s: %s" % (key, _fmt_scalar(value)))
    lines.append("---")
    return "\n".join(lines)


def build_card(meta: Dict[str, Any], body: str) -> str:
    """A complete card file: frontmatter + blank line + body."""
    fm = build_frontmatter(meta)
    return fm + "\n\n" + (body or "").strip() + "\n"


def validate_card(meta: Dict[str, Any], body: str, status: str) -> List[str]:
    """Validate the small, stable contract shared by every persisted card."""
    errors: List[str] = []
    if not str(meta.get("schema_version", "")).startswith("okf.v1"):
        errors.append("schema_version must start with okf.v1")
    if not str(meta.get("name", "")).strip():
        errors.append("name is required")
    if status not in ("draft", "verified"):
        errors.append("status must be draft or verified")
    if meta.get("status") != status:
        errors.append("frontmatter status must match storage status")
    verified = meta.get("verified")
    if status == "verified" and verified is not True:
        errors.append("verified cards must set verified: true")
    if status == "draft" and verified is True:
        errors.append("draft cards cannot set verified: true")
    if status == "verified" and not normalize_sources(meta.get("sources")):
        errors.append("verified cards require at least one source")
    try:
        if int(meta.get("version", 0) or 0) < 1:
            errors.append("version must be a positive integer")
    except (TypeError, ValueError):
        errors.append("version must be a positive integer")
    if not (body or "").strip():
        errors.append("body is required")
    return errors


def normalize_sources(sources: Any) -> List[Dict[str, Any]]:
    """Accept a list of strings or dicts and normalize to dict entries."""
    out: List[Dict[str, Any]] = []
    if isinstance(sources, str):
        sources = [sources]
    if not isinstance(sources, list):
        return out
    for s in sources:
        if isinstance(s, str):
            s = {"path": s}
        if isinstance(s, dict) and s.get("path"):
            entry: Dict[str, Any] = {"path": str(s["path"])}
            for f in ("lines", "function", "commit", "url", "pinned", "author"):
                if f in s and s[f] is not None:
                    entry[f] = s[f]
            out.append(entry)
    return out


def extract_sources(meta: Dict[str, Any]) -> List[Dict[str, Any]]:
    return normalize_sources(meta.get("sources"))


def body_without_fm(text: str) -> str:
    _, body = parse_frontmatter(text)
    return body
