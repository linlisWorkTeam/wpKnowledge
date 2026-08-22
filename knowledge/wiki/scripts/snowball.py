#!/usr/bin/env python3
"""
引文滚雪球：从核心论文出发，向前（references）向后（citations）挖相关论文。
用法：python3 snowball.py [--min-year 2023] [--min-cites 0] [--top 60]
输出：/tmp/snowball_results.md（Markdown 表格，可直接粘贴进 candidate-pool.md）
"""
import json, time, urllib.request, urllib.parse, sys, argparse

# 核心论文：与知识飞轮直接相关的锚点（可增删）
CORE_PAPERS = [
    ("RepoAgent", "2402.16667"),
    ("DocAgent", "2504.08725"),
    ("Reflexion", "2303.11366"),
    ("Self-Refine", "2303.17651"),
    ("CRITIC", "2303.13023"),
    ("Self-Debugging", "2304.05128"),
    ("Promptbreeder", "2309.16797"),
    ("RepoRepair", "2603.01048"),
    ("Code-QA-Bench", "2605.29277"),
    ("SEW", "2505.18646"),
    ("Self-Evolving Survey", "2507.21046"),
    ("Feedback Over Form", "2604.12345"),  # 占位，若 S2 查不到会自动跳过
]

def api_get(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'research-snowball/1.0'})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            if attempt == 2:
                print(f"  ERROR {url[:80]}: {e}", file=sys.stderr)
                return None
            time.sleep(3)

def get_paper(arxiv_id):
    d = api_get(f"https://api.semanticscholar.org/graph/v1/paper/arXiv:{arxiv_id}?fields=title,year,citationCount,venue,externalIds,authors.name")
    if not d or 'paperId' not in d:
        return None
    return d

def get_refs(paper_id, direction):
    # direction: 'references' (向后=它引用的) or 'citations' (向前=引用它的)
    results = []
    offset = 0
    while True:
        url = (f"https://api.semanticscholar.org/graph/v1/paper/{paper_id}/{direction}"
               f"?fields=title,year,citationCount,venue,externalIds&limit=100&offset={offset}")
        d = api_get(url)
        if not d or not d.get('data'):
            break
        for item in d['data']:
            p = item.get('citedPaper') or item.get('citingPaper') or {}
            results.append(p)
        if offset + 100 >= d.get('total', 0):
            break
        offset += 100
        time.sleep(1.5)
    return results

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--min-year', type=int, default=0)
    ap.add_argument('--min-cites', type=int, default=0)
    ap.add_argument('--top', type=int, default=60)
    args = ap.parse_args()

    all_candidates = {}
    seen_papers = set()

    for name, arxiv_id in CORE_PAPERS:
        print(f"\n=== {name} ({arxiv_id}) ===")
        p = get_paper(arxiv_id)
        if not p:
            print("  paper not found on S2, skip")
            continue
        seen_papers.add(arxiv_id)
        for direction in ['references', 'citations']:
            print(f"  -- {direction} --")
            items = get_refs(p['paperId'], direction)
            for it in items:
                ext = it.get('externalIds') or {}
                aid = ext.get('ArXiv') or ext.get('arXiv')
                if not aid:
                    continue
                aid = aid.split('v')[0]
                if aid in seen_papers:
                    continue
                year = it.get('year') or 0
                cites = it.get('citationCount') or 0
                if year < args.min_year or cites < args.min_cites:
                    continue
                info = {
                    'title': it.get('title', ''), 'year': year,
                    'venue': it.get('venue', ''), 'citationCount': cites,
                    'arxiv': aid,
                }
                if aid in all_candidates:
                    if cites > all_candidates[aid]['citationCount']:
                        all_candidates[aid] = info
                else:
                    all_candidates[aid] = info
            time.sleep(1.5)

    ranked = sorted(all_candidates.values(), key=lambda x: -x['citationCount'])[:args.top]
    print(f"\n\n===== 候选论文共 {len(all_candidates)} 篇，取前 {len(ranked)} =====\n")
    lines = ["| # | arXiv | 年份 | 引用 | 标题 |", "|---|-------|------|------|------|"]
    for i, r in enumerate(ranked):
        lines.append(f"| {i+1} | {r['arxiv']} | {r['year']} | {r['citationCount']} | {r['title'][:80].replace('|', '/')} |")
        print(f"{i+1}. [{r['arxiv']}] ({r['year']}) cites={r['citationCount']} {r['title'][:90]}")
        if r['venue']:
            print(f"     venue: {r['venue'][:80]}")

    md = "\n".join(lines)
    with open('/tmp/snowball_results.md', 'w') as f:
        f.write(md + "\n")
    with open('/tmp/snowball_results.json', 'w') as f:
        json.dump(ranked, f, ensure_ascii=False, indent=2)
    print("\nSaved to /tmp/snowball_results.md and /tmp/snowball_results.json")

if __name__ == '__main__':
    main()
