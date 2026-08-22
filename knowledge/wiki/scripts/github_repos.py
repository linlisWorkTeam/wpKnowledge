#!/usr/bin/env python3
"""
GitHub 高 star 活跃仓库检索：按主题搜仓库，过滤 ⭐≥1000 + 近12个月活跃 + 未归档。
用法：python3 github_repos.py
输出：/tmp/github_repos_results.md（Markdown 表格）
注意：GitHub 搜索 API 未认证限 10 req/min，脚本内置限速；建议配 GH_TOKEN 环境变量。
"""
import json, time, os, urllib.request, urllib.parse, sys

# 主题查询：与飞轮各环节相关的关键词组合
QUERIES = [
    "code documentation generator language:Python stars:>500 pushed:>2025-08-01",
    "code documentation LLM stars:>500 pushed:>2025-08-01",
    "knowledge base coding agent stars:>500 pushed:>2025-08-01",
    "self improving agent stars:>500 pushed:>2025-08-01",
    "repository code understanding stars:>500 pushed:>2025-08-01",
    "code summarization stars:>500 pushed:>2025-08-01",
    "spec driven development stars:>500 pushed:>2025-08-01",
    "retrieval augmented generation code stars:>500 pushed:>2025-08-01",
    "code review agent stars:>500 pushed:>2025-08-01",
    "autonomous coding agent stars:>500 pushed:>2025-08-01",
]

MIN_STARS = 1000  # 准入门槛

def api_get(url):
    headers = {'User-Agent': 'research-gh/1.0', 'Accept': 'application/vnd.github+json'}
    token = os.environ.get('GH_TOKEN', '')
    if token:
        headers['Authorization'] = f'token {token}'
    req = urllib.request.Request(url, headers=headers)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            if attempt == 2:
                print(f"  ERROR {url[:80]}: {e}", file=sys.stderr)
                return None
            time.sleep(5)

results = {}
for q in QUERIES:
    print(f"\n=== {q} ===")
    url = ("https://api.github.com/search/repositories"
           f"?q={urllib.parse.quote(q)}&sort=stars&order=desc&per_page=30")
    d = api_get(url)
    if not d:
        continue
    for it in d.get('items', []):
        full = it['full_name']
        stars = it['stargazers_count']
        pushed = (it.get('pushed_at') or '')[:10]
        archived = it.get('archived', False)
        if stars < MIN_STARS or archived:
            continue
        info = {
            'repo': full, 'stars': stars, 'pushed': pushed,
            'desc': (it.get('description') or '')[:100],
            'url': it['html_url'],
        }
        if full in results:
            if stars > results[full]['stars']:
                results[full] = info
        else:
            results[full] = info
    time.sleep(7)  # 未认证限速 10/min

ranked = sorted(results.values(), key=lambda x: -x['stars'])
print(f"\n\n===== 达标仓库（⭐≥{MIN_STARS} 且近12个月活跃）共 {len(ranked)} 个 =====\n")
lines = ["| # | 仓库 | ⭐ | 最近push | 描述 |", "|---|------|----|---------|------|"]
for i, r in enumerate(ranked):
    lines.append(f"| {i+1} | [{r['repo']}]({r['url']}) | {r['stars']} | {r['pushed']} | {r['desc'].replace('|', '/')} |")
    print(f"{i+1}. {r['repo']} ⭐{r['stars']} pushed={r['pushed']} {r['desc'][:80]}")

md = "\n".join(lines)
with open('/tmp/github_repos_results.md', 'w') as f:
    f.write(md + "\n")
print("\nSaved to /tmp/github_repos_results.md")
