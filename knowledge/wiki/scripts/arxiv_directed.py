#!/usr/bin/env python3
"""
arXiv 定向检索（备用通道）：Semantic Scholar 限速时的替代方案。
用法：python3 arxiv_directed.py
输出：/tmp/arxiv_directed_results.md
"""
import json, time, urllib.request, urllib.parse, re, sys

# 查询词：(关键词, 起始年份)
QUERIES = [
    ("code documentation generation", 2024),
    ("repository-level code understanding", 2023),
    ("code summarization", 2024),
    ("automatic documentation generation", 2024),
    ("self-improving code generation", 2023),
    ("self-correction code generation", 2024),
    ("feedback-driven code generation", 2024),
    ("self-evolving software agents", 2025),
    ("knowledge base for coding agents", 2024),
    ("documentation to code", 2024),
    ("specification-driven code generation", 2024),
    ("retrieval-augmented code generation", 2024),
    ("code generation evaluation benchmark", 2024),
    ("documentation quality evaluation", 2024),
]

def arxiv_search(query, min_year, max_results=15):
    q = urllib.parse.quote(f'all:"{query}"')
    url = (f"http://export.arxiv.org/api/query?search_query={q}"
           f"&start=0&max_results={max_results}"
           f"&sortBy=relevance&sortOrder=descending")
    req = urllib.request.Request(url, headers={'User-Agent': 'research-arxiv/1.0'})
    with urllib.request.urlopen(req, timeout=30) as r:
        xml = r.read().decode()
    entries = re.findall(r'<entry>(.*?)</entry>', xml, re.S)
    out = []
    for e in entries:
        title = re.search(r'<title>(.*?)</title>', e, re.S)
        pub = re.search(r'<published>(.*?)</published>', e, re.S)
        aid = re.search(r'<id>http://arxiv.org/abs/(.*?)</id>', e, re.S)
        if not title or not aid:
            continue
        title = re.sub(r'\s+', ' ', title.group(1)).strip()
        year = int(pub.group(1)[:4]) if pub else 0
        if year < min_year:
            continue
        out.append({'title': title, 'year': year, 'arxiv': aid.group(1).split('v')[0]})
    return out

results = {}
for q, min_year in QUERIES:
    print(f"=== {q} (since {min_year}) ===", flush=True)
    try:
        items = arxiv_search(q, min_year)
    except Exception as e:
        print(f"  ERROR: {e}", file=sys.stderr)
        time.sleep(5)
        continue
    for it in items:
        aid = it['arxiv']
        if aid not in results:
            results[aid] = it
    time.sleep(3)  # arXiv API 礼貌间隔

ranked = sorted(results.values(), key=lambda x: -x['year'])
print(f"\n===== arXiv 定向检索共 {len(ranked)} 篇 =====\n")
lines = ["| # | arXiv | 年份 | 标题 |", "|---|-------|------|------|"]
for i, r in enumerate(ranked):
    lines.append(f"| {i+1} | {r['arxiv']} | {r['year']} | {r['title'][:80].replace('|', '/')} |")
    print(f"{i+1}. [{r['arxiv']}] ({r['year']}) {r['title'][:85]}")

md = "\n".join(lines)
with open('/tmp/arxiv_directed_results.md', 'w') as f:
    f.write(md + "\n")
print("\nSaved to /tmp/arxiv_directed_results.md")
