# 🔍 链式检索方法（Retrieval Method）

> 更新时间：2026-08-20
> 目标：系统化、可复现地发现知识飞轮相关的高质量论文与开源仓库，避免"随手搜、随手记"的零散调研。

## 1. 方法论：三层漏斗

```
第1层 锚点层    核心论文（已确认相关、可信度高的 8-12 篇）
第2层 滚雪球层  Semantic Scholar 引文图：向前挖 references（它引用了谁）
               + 向后挖 citations（谁引用了它）→ 40-60 篇候选
第3层 定向层    多组主题关键词搜索（Semantic Scholar + GitHub）
               → 补齐引文网络覆盖不到的新方向
最终 人工筛选   按准入标准 + 与飞轮相关性逐篇判断，写详细文档或入候选池
```

## 2. 脚本用法（`../scripts/`）

| 脚本 | 作用 | 用法 |
|------|------|------|
| `snowball.py` | 引文滚雪球：12 篇核心论文 → references/citations 双向挖掘 | `python3 snowball.py [--min-year 2023] [--min-cites 0] [--top 60]` |
| `directed.py` | 定向关键词搜索（Semantic Scholar）：14 组查询词覆盖飞轮各环节 | `python3 directed.py` |
| `arxiv_directed.py` | 定向关键词搜索（arXiv 官方 API，**S2 限速时的备用通道**） | `python3 arxiv_directed.py` |
| `github_repos.py` | GitHub 高 star 仓库：按主题搜 + 自动过滤 ⭐≥1000 且近12个月活跃 | `GH_TOKEN=*** python3 github_repos.py`（配 token 提高限速） |

输出：`/tmp/*_results.md`（Markdown 表格）+ `.json`（原始数据）。表格可直接粘贴进 candidate-pool.md。

## 3. 各脚本细节

### 3.1 snowball.py — 引文滚雪球

- **核心论文清单**（`CORE_PAPERS` 常量，可增删）：RepoAgent / DocAgent / Reflexion / Self-Refine / CRITIC / Self-Debugging / Promptbreeder / RepoRepair / Code-QA-Bench / SEW / Self-Evolving Survey 等
- 每篇核心论文做 **references（向后=它引用的）** 与 **citations（向前=引用它的）** 双向挖掘
- 按 `citationCount` 降序排名；同 arXiv id 去重保留引用数更高者
- 过滤参数：`--min-year`（年份下限）、`--min-cites`（引用下限）、`--top`（输出条数）
- 注意：Semantic Scholar 未认证限速较宽松（约 1 req/秒），脚本内置 3 次重试 + 退避

### 3.2 directed.py — 定向关键词检索

- 14 组查询词按飞轮主题分组：文档生成 / 反馈循环 / 知识格式 / 评测门禁
- 年份下限 `min_year` 默认 2023-2025（随主题调整），上限 2026
- 同 arXiv id 去重；按引用数降序

### 3.3 github_repos.py — GitHub 高 star 仓库

- 10 组主题查询，`sort=stars&order=desc`
- **自动过滤**：`MIN_STARS=1000`（准入门槛）+ `pushed_at` 近 12 个月 + 未归档
- 查询词里已带 `pushed:>2025-08-01` 缩小范围；限速 7 秒/请求（未认证 10 req/min）
- 建议配 `GH_TOKEN` 环境变量（认证后 30 req/min）

### 3.4 papers.cool — 沉浸式论文发现（手动补充渠道）

> 网址：https://papers.cool（苏剑林/kexue.fm 出品）
> 搜索 URL：`https://papers.cool/arxiv/search?highlight=1&query=<关键词>`（URL 编码）
> 单篇页：`https://papers.cool/arxiv/<arXiv-ID>`

- **语义搜索**：按相关性排序（返回上限 1000 条），比 arXiv 官方按日期排序好用；关键词命中在摘要中高亮
- **REL 相关论文**：每条结果带 `[REL]` 按钮，给出相关论文（共引/相似网络），是引文滚雪球的补充视角
- **顶会聚合**：首页按 Venue 分类（NeurIPS / ICLR / ICML / EMNLP / ACL / CVPR 等 22 个），适合顶会定向检索
- **Kimi 集成**：每条论文带 `[Kimi]` 按钮可 AI 解读
- 用法：手动补充 Semantic Scholar / arXiv API 覆盖不到的新论文，或顶会（ICSE/FSE/ASE）定向检索

## 4. 准入标准（与 research/README.md 一致）

| 来源类型 | 准入要求 |
|---------|---------|
| 单纯开源仓库 | ⭐≥1000 且近 12 个月活跃、未归档 |
| 论文附属仓库 | 豁免，随论文收录 |
| 设计核心参考 | cannbot / OKF 锚点仓库，官方维护即收录 |
| 论文 | 顶会 ≥ arXiv；越新越好（2025-2026 优先）+ 活跃开源仓库 |

## 5. 检索轮次记录

| 轮次 | 日期 | 方法 | 结果 |
|------|------|------|------|
| 第1轮 | 2026-08-20 | 8 篇核心滚雪球 + 7 组定向关键词 | 44 + 12 候选 → candidate-pool.md（40+ 篇） |
| 第2轮 | 2026-08-20 | 扩展核心集（12 篇）+ 14 组定向词（S2 429 限速 → 切 arXiv API）+ GitHub 高 star 检索 | 60 论文 + 64 仓库 → candidate-pool.md 扩充至 100+ 条目 + 新单篇 |
| 第3轮 | 2026-08-20 | papers.cool 语义搜索 5 主题（文档生成/知识库/规格驱动/仓库理解/反馈驱动） | +35 篇新候选（含 TDD 专项组、CASCADE、Spec Growth Engine、Executable Code Knowledge 等） |
| 第4轮 | 2026-08-21 | 顶会线：DBLP 不可达（网络屏蔽）→ 改用 arXiv cs.SE 分类 6 组关键词 | +8 篇（TDD 理论/Do Code LMs Use Tests/规格悖论/SDD 企业实证等） |

## 6. 注意事项（踩过的坑）

- **arXiv 默认按日期排序**会返回无关论文 → 必须 relevance 排序 + 时间过滤（Semantic Scholar 天然按相关性）
- **Semantic Scholar 对 2025 年后新论文覆盖延迟**：太新的论文可能查不到引用关系 → 用 GitHub 检索 / 顶会官网补充
- **web_extract 后端不可用**时改用 API 脚本（见上）
- **论文"最新 ≠ 最可信"**：预印本无同行评审，自改进领域普遍乐观偏差（见 feedback-loop/fragility-self-improving.md）
