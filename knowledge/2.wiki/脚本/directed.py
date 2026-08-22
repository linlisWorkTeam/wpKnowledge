#!/usr/bin/env python3
"""
定向检索：用 Semantic Scholar 搜索 + 过滤，找知识飞轮相关论文。
用法：python3 directed.py
输出：/tmp/directed_results.md（Markdown 表格）
"""
import json, time, urllib.request, urllib.parse, sys

# 查询词：(关键词, 起始年份)。按飞轮主题分组
QUERIES = [
    # 文档生成（飞轮第一步）
    ("code documentation generation LLM", 2024),
    ("repository level code understanding", 2023),
    ("code summarization large language model", 2024),
    ("automatic documentation generation repository", 2024),
    # 反馈循环（飞轮第三步+第四步）
    ("self improving code generation", 2023),
    ("self correction code generation agent", 2024),
    ("feedback driven code generation", 2024),
    ("self evolving software agents", 2025),
    # 知识格式
    ("knowledge base for coding agents", 2024),
    ("documentation to code generation", 2024),
    ("specification driven code generation", 2024),
    ("retrieval augmented code generation repository", 2024),
    # 评测/门禁
    ("code generation evaluation benchmark", 2024),
    ("documentation quality evaluation", 2024),
]

def api_get(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'research-dir/1.0'})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        print(f"  ERROR: {e}", file=sys.stderr)
        return None

def search(query, min_year):
    url = ("https://api.semanticscholar.org/graph/v1/paper/search"
           f"?query={urllib.parse.quote(query)}&limit=20&year={min_year}-2026"
           "&fields=title,year,citationCount,venue,externalIds,authors.name,abstract")
    d = api_get(url)
    return d.get('data', []) if d else []

results = {}
for q, min_year in QUERIES:
    print(f"\n=== {q} (since {min_year}) ===")
    try:
        items = search(q, min_year)
    except Exception as e:
        print(f"  ERROR: {e}")
        continue
    for it in items:
        ext = it.get('externalIds') or {}
        aid = ext.get('ArXiv') or ext.get('arXiv')
        if not aid:
            continue
        aid = aid.split('v')[0]
        info = {
            'title': it.get('title', ''), 'year': it.get('year'),
            'venue': it.get('venue', ''), 'citationCount': it.get('citationCount', 0),
            'arxiv': aid,
        }
        if aid in results:
            if info['citationCount'] > results[aid]['citationCount']:
                results[aid] = info
        else:
            results[aid] = info
    time.sleep(6)

ranked = sorted(results.values(), key=lambda x: -x['citationCount'])
print(f"\n\n===== 定向检索共 {len(ranked)} 篇 =====\n")
lines = ["| # | arXiv | 年份 | 引用 | 标题 |", "|---|-------|------|------|------|"]
for i, r in enumerate(ranked):
    lines.append(f"| {i+1} | {r['arxiv']} | {r['year']} | {r['citationCount']} | {r['title'][:80].replace('|', '/')} |")
    print(f"{i+1}. [{r['arxiv']}] ({r['year']}) cites={r['citationCount']} {r['title'][:85]}")
    if r['venue']:
        print(f"     venue: {r['venue'][:70]}")

md = "\n".join(lines)
with open('/tmp/directed_results.md', 'w') as f:
    f.write(md + "\n")
with open('/tmp/directed_results.json', 'w') as f:
    json.dump(ranked, f, ensure_ascii=False, indent=2)
print("\nSaved to /tmp/directed_results.md and /tmp/directed_results.json")
