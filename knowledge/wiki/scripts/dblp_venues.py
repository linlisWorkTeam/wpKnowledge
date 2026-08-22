#!/usr/bin/env python3
"""
DBLP 顶会检索：抓 ICSE/FSE/ASE 2025-2026 论文集，关键词过滤飞轮相关论文。
用法：python3 dblp_venues.py
输出：/tmp/dblp_venues_results.md
"""
import urllib.request, re, json, time

# (会议, 年份, DBLP 卷 ID)
VENUES = [
    ("ICSE", 2025, "icse2025"),
    ("ICSE", 2026, "icse2026"),
    ("FSE", 2025, "fse2025"),
    ("FSE", 2026, "fse2026"),
    ("ASE", 2025, "ase2025"),
    ("ASE", 2026, "ase2026"),
]

# 飞轮相关关键词（匹配标题）
KEYWORDS = [
    "documentation", "code summar", "code generation", "code understand",
    "repository", "program repair", "test generation", "specification",
    "spec-driven", "LLM agent", "coding agent", "knowledge", "feedback",
    "self-improv", "self-evolv", "refinement", "code review", "API",
    "retrieval-augment", "RAG", "large language model", "LLM",
]

def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'research-dblp/1.0'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode()

def parse_entries(html):
    """解析 DBLP 会议卷 HTML 里的 <li class=entry> 块。"""
    entries = []
    # 每个 entry: <li class="entry inproceedings">...<span class="title">...</span>...<a href=...>
    blocks = re.split(r'<li class="entry', html)[1:]
    for b in blocks:
        title_m = re.search(r'<span class="title">(.*?)</span>', b, re.S)
        if not title_m:
            continue
        title = re.sub(r'<[^>]+>', '', title_m.group(1)).strip()
        title = re.sub(r'\s+', ' ', title)
        # DOI 链接
        doi_m = re.search(r'<a href="(https://doi\.org/[^"]+)"', b)
        doi = doi_m.group(1) if doi_m else ''
        entries.append({'title': title, 'doi': doi})
    return entries

results = {}
for venue, year, vid in VENUES:
    print(f"=== {venue} {year} ({vid}) ===", flush=True)
    try:
        html = fetch(f"https://dblp.org/db/conf/{'kbse' if venue=='ASE' else 'sigsoft' if venue=='FSE' else ''}{vid}.html")
    except Exception as e:
        print(f"  ERROR: {e}", file=sys.stderr)
        continue
    entries = parse_entries(html)
    print(f"  共 {len(entries)} 篇，过滤关键词中...")
    hits = []
    for e in entries:
        t = e['title'].lower()
        if any(k in t for k in KEYWORDS):
            hits.append(e)
    results[f"{venue}{year}"] = hits
    for h in hits[:20]:
        print(f"    - {h['title'][:90]}")
    time.sleep(2)

# 输出 markdown
lines = ["# DBLP 顶会检索结果（ICSE/FSE/ASE 2025-2026）", ""]
total = 0
for key in sorted(results.keys()):
    hits = results[key]
    total += len(hits)
    lines.append(f"## {key}（命中 {len(hits)} 篇）")
    lines.append("")
    for h in hits:
        lines.append(f"- {h['title']}")
        if h['doi']:
            lines.append(f"  DOI: {h['doi']}")
    lines.append("")
lines.append(f"**总计命中 {total} 篇**")
with open('/tmp/dblp_venues_results.md', 'w') as f:
    f.write("\n".join(lines) + "\n")
print(f"\nSaved to /tmp/dblp_venues_results.md (total {total})")
