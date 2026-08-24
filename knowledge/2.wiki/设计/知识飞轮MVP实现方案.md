# endlessWpKnowledgeRunner — 知识飞轮设计总结与 MVP 实现方案

> 本文档基于对 wpKnowledge 仓库全部调研文档（`knowledge/2.wiki/设计/*` 正式设计文档 + `knowledge/2.wiki/研究/*` 主题化调研材料 + 候选池、`knowledge/1.dshAnalysis/*`、`knowledge/3.workpanel/*` 与两个参考仓库 OKF / cannbot 的深度笔记）的系统阅读与收敛。
> 它回答一个问题：**把「知识飞轮」从纸面设计落成一个可运行、可扩展的 MVP，应该怎么设计？**

---

## 0. Repository boundary (current layout)

The implementation is under `endlessWpKnowledgeRunner/`; the publishable OKF
bundle is the repository-level `knowledge/` directory. New raw material goes
to `knowledge/inbox/`, verified cards go to `knowledge/concepts/`, drafts go to
`knowledge/drafts/`, protected revisions go to `knowledge/history/`, and
feedback/log/cursor state goes to `knowledge/runtime/`. The runner is the only
writer of card and runtime files; agents enter through `fw_ingest` or
`python fw.py ingest`.

The detailed directory and write contract is maintained in
[`KNOWLEDGE-REPOSITORY.md`](KNOWLEDGE-REPOSITORY.md).

## 1. 飞轮是什么：一个 Loop，由四个环节组成

调研文档（[知识飞轮流程设计](../../knowledge/2.wiki/设计/知识飞轮流程设计.md)、[项目概述](../../knowledge/2.wiki/设计/项目概述.md)、[门禁与评测机制](../../knowledge/2.wiki/设计/门禁与评测机制.md)、[知识飞轮案例](../../knowledge/2.wiki/设计/知识飞轮案例.md)）反复确认同一件事：**飞轮不是一个系统，是一个 loop / workflow**。本仓库已有分析的目标是「源码/知识 → 代码 → 反馈」；本 MVP 把它泛化为更适合「知识仓库运营」的形态，四个环节各自可以由被赋予使命的 agent 承担：

```
                    ┌─────────────────────────────────────────────┐
                    │                                             │
   ┌──────────┐     ▼       ┌──────────────┐      ┌────────────┐  │
   │ ① 获取知识 │ ────────▶ │ ② 沉淀知识 OKF │ ──▶ │ ③ 评测打分 │──┼─┐
   │ Acquire  │   触发式    │ Consolidate  │      │ Evaluate   │  │ │
   └──────────┘   /自动    └──────────────┘      └─────┬──────┘  │ │
                                                      │ 通过门禁  │ │
                    ┌──────────────┐                   ▼          │ │
                    │ ④ 应用知识    │ ◀── 外部检索 ── 合格知识库     │ │
                    │ Apply        │              (concepts/)     │ │
                    └──────────────┘                              │ │
                         ▲                                        │ │
                         └──────── 使用反馈（点击/评分/勘误）───────────────────┘
```

- **① 获取知识（Acquire）**：两个入口。**触发式**：任何 agent / 用户向飞轮推送知识（`fw_ingest` 工具，或往 `knowledge/inbox/` 投递文件）即运行；**自动化**：`liveMode` 启动后，一个 **harvester agent** 周期性扫描来源目录与投放目录，自行提炼知识入库。
- **② 沉淀知识（Consolidate）**：**不使用 RAG**，采用 **OKF 模式**（知识内容直接可 `cat`、可 `git diff`、可评审）。知识 = Markdown + YAML frontmatter 的知识卡（Concept），按 Bundle（目录树）自包含组织，`sources` 溯源 + `status` 状态 + `verified` 信任级别为 first-class（依据 `knowledge/2.wiki/研究/知识格式/Knowledge Catalog与OKF知识格式.md`）。知识库天生可 diff、可评审、可回滚。
- **③ 评测打分（Evaluate）**：一套**多信号打分机制**（详见 §4）。打分是「评测闭环」而非 LLM 自我感觉：客观信号为主，LLM 陪审团为辅，重复评测报告均值±方差，通过门禁才合并（防污染，依据 `flywheel.md §9` + `fragility-self-improving.md`）。
- **④ 应用知识（Apply）**：**只读检索**入口（`fw_query` 工具 + HTTP 端点），供外部消费；检索命中与用户反馈回流为评分信号（依据 cannbot `knowledge-query` + `knowledge-issue-report` 的「生产→治理→消费→反馈」闭环）。

## 2. 设计溯源：这些结论是从哪里来的

| 飞轮环节 | 采纳的关键结论 | 调研依据（仓库内文档） |
|---|---|---|
| 获取（顺序） | 知识处理顺序 = 依赖拓扑序；先依赖后被依赖 | RepoAgent、RepoDoc（`knowledge/2.wiki/研究/文档生成/`） |
| 获取（触发） | 代码/文档变更触发增量更新，而非全量重跑 | RepoAgent、RepoDoc、Code & Doc Churn（candidate-pool） |
| 沉淀（格式） | 知识格式 = OKF：Markdown + frontmatter（sources/status/verified）；Bundle 自包含；index.md 渐进披露；log.md 更新历史 | knowledge-catalog-okf、cannbot-knowledge、knowledge-format.md |
| 沉淀（形态） | 知识 = 解释型文档：伪代码/要点 + 为什么这样、解决什么问题、适用场景；**保留"魂"不搬运"壳"**；低质文档不如没有 | knowledge-format.md、llm-api-docs（Code2Doc） |
| 评测（信号） | 多信号组合：结构 + 溯源 + 时效 + 去重 + 客观一致性；单一指标必误判 | gate.md §3.5、research-brief 结论 9 |
| 评测（客观性） | 外部验证 > 内部反思；LLM 自评不可作主信号；防作弊（评测集独立） | critic.md、fragility-self-improving.md、code-qa-bench.md |
| 评测（可靠性） | 重复评测 ≥ 5 次报告均值±方差；规格定义到可执行级；控制顺序 | fragility-self-improving.md、gate.md §3.5、research-brief 结论 14 |
| 评测（反馈） | 结构化信号 + 自然语言解读两层；执行反馈最有效 | self-debugging.md、feedback-over-form.md、flywheel.md §5 |
| 应用（检索） | 多路召回 + 质量重排；证据充分性规则（weak 不能单独支撑结论）；检索可审计 | cannbot-knowledge §5、retrieval-method.md |
| 全生命周期 | 知识「生产→治理→消费→反馈」流程锚点 | cannbot-knowledge、sok-agentic-skills（技能生命周期 7 阶段） |
| 可靠性硬约束 | 防污染（未过门禁不合并 + 回滚）、防脆弱（方差/顺序/规格）、知识库是攻击面（来源可信） | flywheel.md §9、conself、FDI/RAG 投毒（candidate-pool） |

## 3. 角色分工（谁可以碰知识）

继承 `flywheel.md §3` 的三角色分离，但针对「知识运营」场景简化为两方 + 一个编排层：

| 角色 | 职责 | 是否允许修改知识 |
|---|---|---|
| 推送方（触发 agent / 用户） | 通过 `fw_ingest` 投递知识原文或文件；只读检索 `fw_query` | ❌ 不直接写 store（由 ingest 管道写 draft） |
| **harvester agent**（liveMode） | 扫描来源 → 自行提炼结构化知识 → 交给 ingest 管道 | ❌ 只产出 draft payload，不直接落知识卡 |
| **编排层（runner 自身的确定性管道）** | OKF 化（frontmatter 补齐）→ 打分 → 门禁决策 → 合并/退回 → 索引/日志 | ✅ 唯一执笔者（写 store） |
| 消费方（外部 agent / HTTP 调用方） | 检索 + 反馈（命中、评分、勘误 flag） | ❌ 只读；反馈写 ledger（可审计） |

原则（来自调研）：**谁评测谁不改，谁沉淀谁负责**；门禁判断不依赖任何 agent 的自我感觉；评测与生成分离。
MVP 中评测的「生成」环节弱化为「文档一致性」客观信号（见 §4），后续可扩展「知识 → 代码还原」强评测。

## 4. 打分机制（评测环节）：多信号加权 + 门禁 + 重复评测

> `gate.md` 留下了「相似度怎么算、置信度怎么算」的待定项。本 MVP 给出一个**切实可行、可执行到代码级**的打分定义（规则全部确定性可重复），也保留了 LLM 陪审团作为辅助信号。

### 4.1 信号清单（每一项 0~1，可单独开启/关闭）

| 信号 | 权重 | 是什么 / 怎么算 | 依据 |
|---|---|---|---|
| S1 溯源完整性 Provenance | 0.25 | frontmatter 有效；`sources` 非空；来源可解析（文件存在或 http(s) URL）；有 pinned 锚点（文件:行 / commit / URL） | OKF sources；flywheel §4 溯源是归因前提 |
| S2 结构质量 Structure | 0.20 | 有 title/description/正文；有 `##` 分节；有代码块或要点列表；出现「为什么/原因/适用场景」类解释词；长度在合理区间；非整段原文搬运（与来源文本的相似度阈值） | knowledge-format.md（解释型文档）；Code2Doc 防 AI 污染/防搬运 |
| S3 时效 Freshness | 0.10 | 按 `updated_at`/`stale_after` 衰减：越新越满，超期降到 0.5 以下 | OKF status/stale_after；Code2Doc 时效关卡 |
| S4 去重/污染 Dedup | 0.10 | 与 store 中已有概念按 name/内容哈希查重；重复 → 低分；已 verified 概念被改写 → 走版本升级而非新卡 | flywheel §9.5 防污染；Code2Doc 去重 |
| S5 可验证性 Verifiability | 0.05 | 卡内是否给出可验证锚点（数字指标、引用链接、命令、公式），便于外部复核 | OKF Attested Computation（executor/attester 雏形）；cannbot 证据体系 |
| **J 陪审团 LLM Jury** **（可选）** | 0.20 | 模型对「清晰度 / 忠实度 / 可行动性」三项 1~10 打分（相对 sources 核对），**重复 N 次取均值±方差**；未启用或失败时权重重新分配给确定性信号 | critic（外部验证）；fragility（重复评测）；gate §3 候选方向「LLM 打分」作为辅信号 |
| U 使用反馈 Usage | 0.10 | 检索命中数、消费方评分、勘误 flag，从 `ledger.json` 统计；无数据时取中性 0.5，随最后命中时间衰减 | cannbot issue-report；cannbot knowledge-query 充分性规则 |

### 4.2 合成与门禁

- `score = round(100 * Σ (w_i · s_i))`；未启用信号的权重按剩余权重归一化（多信号优雅降级）。
- **门禁**：`score ≥ gate_threshold`（默认 70，可配置；区别于 wiki 中面向「代码还原」的 80% 相似度门禁——那个信号在 MVP 中由 S2/S5 近似，后续扩展环节可直接接入）→ `status: verified` 合并入 `concepts/`；否则留在 `drafts/`，返回「薄弱点清单」。
- **置信度**：`confidence = 1 - min(1, jury_std / 2)`（陪审团一致性强则置信度高）；`fw_eval` 对同一批卡重复打分 ≥3 次报告均值±方差。
- 评测输出 = 结构化分数报告（每信号分 + 原因清单 + 薄弱点），对应 `flywheel.md §5` 的「结构化信号」层；薄弱点即「知识薄弱点地图」的雏形（触发几次扣分 → 标记薄弱）。

### 4.3 为什么这样设计（而不是更复杂的方案）

1. **客观信号优先**（fragility/conself）：S1~S5 全部是确定性规则，重复执行结果一致，不依赖模型状态。
2. **防作弊**（code-qa-bench）：S2 显式惩罚「整段搬运」，S1 要求 sources 溯源可核，J 陪审团要求对照 sources 判忠实度而非凭印象。
3. **防污染**（flywheel §9.5）：未过门禁只进 drafts；已 verified 卡被覆盖必须走版本升级（history/ 保留旧版）；评分低于上一版本的改写会被标记回滚候选。
4. **可演进**：权重、阈值全部在 `config.json`，新信号（如测试通过率、知识→代码还原相似度）按同一接口插拔。

## 5. 目录结构（MVP 落地）

```
endlessWpKnowledgeRunner/
├── README.md                    # 使用入口（怎么触发/怎么查/liveMode）
├── config.json                  # 阈值/权重/来源目录/陪审团开关
├── fw.py                        # CLI 入口：python fw.py <cmd>（standalone 运行，零第三方依赖）
├── fwrunner/
│   ├── __init__.py
│   ├── config.py                # 配置加载（JSON）
│   ├── okf.py                   # OKF 知识卡读写：frontmatter 子集解析/生成、sources 规范化
│   ├── store.py                 # Bundle 存储：drafts/concepts/history、index.md、log.md、ledger
│   ├── ingest.py                # ①获取→②沉淀管道：原稿 → 概念卡(draft) → 打分 → 门禁 → 合并
│   ├── scorer.py                # ③打分引擎：信号计算、合成、置信度、报告（含薄弱点）
│   ├── jury.py                  # LLM 陪审团信号（可插拔：读 DSH 或 API 产出的 JSON）
│   ├── retrieve.py              # ④应用：索引 + BM25 检索 + 质量重排 + 充分性提示
│   ├── livemode.py              # ready 状态机：scan 来源 → 候选清单（供 harvester 消费）
│   ├── ledger.py                # 使用反馈记录：命中/评分/勘误（回流为 Usage 信号）
│   └── util.py                  # CJK tokenize、文本相似度、时间工具
├── dsh/
│   ├── fw-plugin.js             # DSH 动态 Cordis 插件源码（fw_* 工具 + liveMode + HTTP 端点）
│   └── plugin-agent-preset.md   # 如何把插件永久挂进 DSH（agent preset / 开机加载）
├── sources/                     # ①触发式投放目录：往里丢 .md 即被 ingest；examples/ 示例
├── store/                       # ②OKF Bundle（本目录入库 git，即发布）
│   ├── index.md                 # 渐进式披露索引（自动生成）
│   ├── log.md                   # 追加式更新历史（审计）
│   ├── ledger.json              # 使用反馈统计（应用环节回流）
│   ├── .livemode-state.json     # liveMode 扫描游标（已处理文件 + 内容哈希）
│   ├── drafts/                  # 未过门禁的草稿卡
│   ├── concepts/                # 已过门禁的合格知识卡（外部检索只搜这里 + drafts 可选）
│   └── history/                 # version 升级前的旧版快照（防污染回滚）
└── tests/                       # python -m unittest discover（无第三方依赖）
```

## 6. OKF 知识卡模板（沉淀环节产物）

每张知识卡 = 一个 `.md` 文件，frontmatter 对齐 `okf.v1`，正文对齐「解释型文档」规范：

```yaml
---
schema_version: okf.v1
name: workpanel-connecter-architecture        # 概念 ID（= 文件名）
kind: concept
category: architecture
title: WorkPanel Connecter 架构
description: 一句话概括：Connecter 的 P0-P3 分层与消息路由设计
sources:                                      # 溯源（必须，可核）
  - path: knowledge/3.workpanel/调研/WorkPanel Connecter愿景符合度与可扩展性评审.md
    lines: 1-120
    pinned: true
status: verified                               # draft | verified
verified: true                                 # false | true
version: 1                                     # 覆盖更新必须 +1
stale_after: '2027-01-01'                      # 过期日（时效信号）
score: 82                                      # 最近一次评测（只读，由 runner 写）
score_breakdown: { provenance: 0.9, structure: 0.85, ... }   # 信号分
confidence: 0.9
tags: [connecter, workpanel, architecture]
platforms: []                                  # 可选：适用平台过滤
created_at: '2026-08-21T10:00:00+08:00'
updated_at: '2026-08-21T10:00:00+08:00'
---

## 概述
（为什么有这个东西、解决什么问题）

## 设计要点（伪代码/结构 + 为什么）
（保留逻辑"魂"：数据流、边界、调用关系；每条尽量附 sources 锚点）

## 适用场景
（什么时候应该采用这个写法/设计，什么时候不应该）

## 验证
（如何复核这条知识：链接、命令、指标、原始文档位置）
```

## 7. 评测报告结构（结构化信号，可被编排层消费）

```json
{
  "concept": "workpanel-connecter-architecture",
  "score": 82,
  "gate": "pass",
  "signals": {"provenance": 0.9, "structure": 0.85, "freshness": 1.0, "dedup": 1.0, "verifiability": 0.6, "usage": 0.5},
  "jury": {"enabled": false, "runs": 0, "mean": null, "std": null},
  "weak_points": ["verifiability: 无 pinsized 验证锚点，建议补充可复核的文档/代码链接", "structure: 缺少『适用场景』小节"],
  "confidence": 0.9,
  "took_ms": 12
}
```

## 8. 迭代方向（MVP 之后的飞轮闭环）

1. **强评测环**：把 wiki 的「知识→代码→与源码对比」门禁接入 scorer（新增信号：还原相似度 + 测试通过率），实现真正的「评测失败→反馈→知识修订→重测」回路（`flywheel.md` 主线）。
2. **归因修订**：按 sources 反向映射薄弱点到段落（`review/attributor` 思路），让修订 agent 只改被点名的段落。
3. **薄弱点地图持久化**：ledger 中累计各信号失败次数，作为门禁辅助信号。
4. **liveMode 调度升级**：定时任务 + 网页端控制面板 + 检索审计日志。

## 9. 与仓库既有文档的关系

| 仓库文档 | 本 MVP 的对应/差异 |
|---|---|
| `knowledge/2.wiki/设计/知识飞轮流程设计.md` | 四环节是其「源码→知识→代码→反馈」的泛化；角色分离/溯源/反馈结构/防污染全部继承 |
| `knowledge/2.wiki/设计/门禁与评测机制.md` | 打分机制 = gate 的多信号评测的三信号组合落地为五+三信号；80% 阈值语义保留在缓存可配置位置，默认 70（知识卡质量分） |
| `knowledge/2.wiki/设计/知识形态定义.md` | 知识形态 1:1 采用；补全 OKF frontmatter 与知识卡模板 |
| `knowledge/2.wiki/设计/知识飞轮实现方案.md` | 目录/模块结构对齐（config/store/scorer/retrieve）；实现语言同为 Python（MVP 零依赖） |
| `knowledge/2.wiki/设计/知识飞轮CodeAgent迁移方案.md` | 本 MVP 是「CodeAgent 主会话编排」思路的 DSH 落地：DSH 动态插件 = 主会话，harvester = 子 agent，确定性管道 = 脚本化决策 |
| `knowledge/2.wiki/研究/知识格式/*` | OKF = 格式锚点，cannbot = 运营流程锚点，均 1:1 采纳 |
## 10. 当前实现详解：从设计能力到源码行为

本节记录当前 MVP 的真实实现，而不是只描述目标架构。源码基线为 `c8f1d8d25b39edfeea0c9aa712f8b541159a6872`，实现语言为 Python 3.8+ 标准库；DSH 适配层使用 JavaScript。整体调用链如下：

```text
文件 / stdin / DSH fw_ingest
        │
        ▼
fw.py -> Ingester.run
        │  解析 frontmatter、补元数据、计算 source
        ▼
Scorer.score_concept
        │  provenance / structure / freshness / dedup
        │  verifiability / jury / usage
        ▼
score >= threshold ?
        ├─ pass -> store/concepts/<name>.md
        └─ fail -> store/drafts/<name>.md
                       │
                       ├─ history/ 保护旧 verified 版本
                       ├─ index.md / log.md
                       └─ ledger.json / liveMode state
        ▼
Retriever.search -> BM25 + quality rerank -> feedback
```

### 10.1 知识获取（Acquire）

**触发式获取**由 `fw.py ingest` 或 DSH 的 `fw_ingest` 触发；输入可以是 `--file`、`--content` 或 stdin。`Ingester.run` 先读取正文，再从已有 OKF frontmatter、命令行参数和文件路径合并出概念名、描述、分类、标签和来源。

**自动获取**由 liveMode 的 `scan` 找出新增/变更文件，再由 DSH 插件启动 harvester agent 提炼结构化 JSON。harvester 只产出 `name/title/description/category/tags/content/sources`，不直接写 Store；最终仍必须回到同一条 `fw_ingest -> score -> gate` 管道。

实现映射：

| 能力 | 实现位置 | 主要输入/输出 |
|---|---|---|
| CLI 入口 | `fw.py:49-121` | 参数或 stdin -> JSON 结果 |
| 规范化获取 | `fwrunner/ingest.py:54-135` | 原始文本/文件 -> draft Concept |
| DSH 工具适配 | `dsh/fw-plugin.js:167-216` | `fw_ingest` -> Python CLI |
| Agent 获取 | `dsh/fw-plugin.js:77-125` | 来源文件 -> structured payload |

### 10.2 格式化沉淀（OKF Consolidate）

知识卡使用 Markdown 正文 + YAML-like frontmatter。`okf.py` 自己实现了一个无第三方依赖的 YAML 子集解析器和 emitter，支持标量、简单列表、列表映射和 `sources` 归一化。

写入时，runner 会补齐或维护：

- `schema_version: okf.v1`；
- `name/title/description/sources`；
- `status`、`verified`、`version`；
- `created_at/updated_at`；
- runner 计算的 `score/confidence/score_breakdown`。

知识卡的物理位置就是状态机：`store/concepts/` 表示 verified，`store/drafts/` 表示 draft。`store/index.md` 是可读索引，`store/log.md` 是追加日志，`store/ledger.json` 是反馈和内容 hash 台账。

实现映射：`fwrunner/okf.py:81-245`、`fwrunner/store.py:49-71,118-127,224-266`。

### 10.3 自动评分（Evaluate）

`Scorer.score_concept` 为每张卡计算 0 到 1 的信号，再按配置权重归一化为 0 到 100 分：

```text
score = 100 * sum(active_weight * signal) / sum(active_weight)
gate = score >= gate.threshold
```

当前默认信号和实现规则：

| 信号 | 当前实现 |
|---|---|
| provenance | 检查 `schema_version`、sources、pinned/lines/commit/url，以及文件或 URL 是否可解析 |
| structure | 检查 name、description、`##` 章节、代码块/列表、解释性词、长度和正文复制相似度 |
| freshness | 根据 `updated_at` 和 `stale_after` 做时间衰减 |
| dedup | 对正文做 SHA-256，并与 ledger 和 Store 中已有正文比较 |
| verifiability | 统计 URL、代码围栏、命令、数字/百分比等验证锚点 |
| jury | 可选读取 `store/jury/<name>.json`，对多次外部评分计算均值和标准差 |
| usage | 从 `ledger.json` 读取命中、rating、correct 和最近使用时间 |

`config.json` 是评分规则的可执行配置：默认门槛 70，jury 默认关闭；未启用的 jury 权重会重新分配给其余信号。`fw_score` 持久化最新信号，`fw_eval` 重复评分并报告 mean/std/min/max，但重复同一确定性函数不能替代独立外部验证。

实现映射：`fwrunner/scorer.py:54-303`、`fwrunner/config.py:7-49`。

### 10.4 draft / verified 门禁

门禁只在 `Ingester.run` 的入库路径上决定状态：

1. 创建临时 draft 视图并评分；
2. pass 且没有 `force_draft` 时，写入 `concepts/`，设置 `status=verified`、`verified=true`；
3. fail 或显式 `force_draft` 时，写入 `drafts/`，设置 `status=draft`、`verified=false`；
4. 返回报告和 weak points，便于上层 Agent 或 Dashboard 展示。

已有 verified 卡收到更差的新版本时，旧卡不会被覆盖；新内容进入 drafts，返回结果仍指出当前 verified 版本被保留。这是防止低质量 Agent 输出污染知识库的核心约束。

注意：当前 `fw_score`/`fw_eval` 只负责重新计算和报告，不负责把已有 draft 自动迁移为 verified；真正的状态迁移仍需要重新走 ingest/review 策略。

实现映射：`fwrunner/ingest.py:136-225`。

### 10.5 历史版本保护

当同名 verified 概念被成功更新时，runner：

1. 读取旧版本的 `version`；
2. 将旧 frontmatter + 正文写入 `store/history/<name>/v<old_version>.md`；
3. 新版本号加一后写入 `store/concepts/<name>.md`。

如果新版本评分失败，历史快照仍保留，但 verified 卡继续留在 `concepts/`，新候选落在 `drafts/`。因此版本升级和质量门禁共同形成“可回看、可 diff、可人工恢复”的保护层。

实现映射：`fwrunner/ingest.py:136-155`、`fwrunner/store.py:78-81,129-137`。

### 10.6 BM25 检索（Apply）

`Retriever.search` 默认只读取 verified 概念，也可以显式指定 `status=draft` 或开启配置中的 `include_drafts`。每张卡将以下字段合并进索引，并使用不同字段权重：

```text
name 3.0 / title 3.0 / description 2.0 / tags 2.0 / body 1.0
```

查询过程是：

1. 对中文生成单字和双字 token，对英文/数字生成词 token；
2. 计算简化 BM25；
3. 将 BM25 归一化；
4. 与 `score / 100` 做质量重排；
5. 返回 name、score、version、sources、snippet 等信息。

排序公式：

```text
relevance = normalized_bm25 * (1 - quality_weight)
          + score/100 * quality_weight
```

CLI/DSH 的普通查询默认会记录命中反馈；Dashboard 查询显式使用 read-only 模式，避免“搜索结果展示”自动放大 usage。

实现映射：`fwrunner/retrieve.py:27-136`、`fwrunner/util.py:21-51`。

### 10.7 使用反馈（Feedback）

反馈写入 `store/ledger.json`，分为：

- `hit`：命中或显式取回；
- `rate`：0 到 5 的用户评分；
- `correct`：标记知识需要纠正。

`usage_signal` 会综合命中次数、评分、纠错次数和距上次使用的天数，生成 0 到 1 的 usage 信号，参与下一次评分。反馈本身不会直接改正文，也不会跳过 gate。

当前实现是“反馈影响质量分”的第一步；`correct` 尚未自动生成修订任务、定位来源段落或启动 Agent 重写。完整的“纠错 -> 归因 -> 修订 -> 重测”仍是后续迭代项。

实现映射：`fwrunner/store.py:139-189`、`fw.py:191-193`。

### 10.8 liveMode 自动扫描

Python 侧 `livemode.scan`：

1. 遍历 `source_dirs + watch_dirs`；
2. 只处理 Markdown；
3. 跳过 `.git`、`__pycache__`、`node_modules`、`history`、`jury` 等目录；
4. 跳过 README、index、log、ledger 等管理文件；
5. 计算文件 SHA-256；
6. 与 `.livemode-state.json` 和 `ledger.json` 对比，过滤未变更/已入库文件；
7. 按 mtime 升序返回候选，默认每轮最多 4 个。

DSH 插件用宿主 timer 每 15 分钟执行一轮：扫描候选、启动 harvester、读取 structured JSON，再调用 `fw_ingest`。Agent 提炼失败时回退为直接 ingest 原始文件。处理后的文件 hash 和概念名写入 `.livemode-state.json`，避免下一轮重复列出。

实现映射：`fwrunner/livemode.py:17-78`、`dsh/fw-plugin.js:74-162,339-416`。

### 10.9 Dashboard 可视化

Dashboard 是独立的零依赖本地前台，不替换 Store，也不复制一套评分逻辑：

```powershell
cd D:\AI\wpKnowledge\endlessWpKnowledgeRunner
python web/server.py
```

默认访问 `http://127.0.0.1:4174/`。服务器直接加载当前 runner 的 `Store/Scorer/Retriever/livemode`，前端通过同源 API 获取数据：

| API | 用途 | 是否写入数据 |
|---|---|---:|
| `GET /api/status` | 总数、verified/draft、平均分、反馈数、最近日志 | 否 |
| `GET /api/concepts` | 知识卡列表与筛选 | 否 |
| `GET /api/concepts/<name>` | 正文、来源、信号、版本详情 | 否 |
| `GET /api/query?q=...` | BM25 查询 | 否，Dashboard 显式禁用命中反馈 |
| `GET /api/scan` | liveMode 候选扫描 | 可能推进扫描游标 |
| `POST /api/feedback` | rate/correct/hit | 是 |
| `POST /api/rescore` | 重新计算并写回评分字段 | 是 |

页面布局分为四块：顶部状态统计、左侧知识卡列表、中间详情和评分信号、底部运行日志；按钮只调用 runner 已有能力，不直接修改 Markdown 正文。`web/` 下的 HTML/CSS/JS 不依赖 React、Node 或第三方 Python 包。

实现映射：`web/server.py`、`web/dashboard.html`、`web/app.js`、`web/styles.css`。

## 11. 当前运行验证与证据边界

当前实现可以用以下命令复核：

```powershell
cd D:\AI\wpKnowledge\endlessWpKnowledgeRunner
python -m unittest discover -s tests -v
python fw.py status --json
python fw.py query --q "connecter" --no-feedback --json
python fw.py eval --name workpanel-connecter --runs 5 --json
python web/server.py
```

已验证能力包括：15 项 Python 单元测试通过、CLI status/query/eval 可运行、Dashboard HTTP 页面和 API 可访问、真实浏览器可渲染知识卡和评分信号、检索交互可用。

仍未由本设计文档宣称为生产能力的部分：文件写入没有事务/锁，Dashboard 没有认证和权限，liveMode timer 依赖 DSH 进程生命周期，OKF 解析器是 YAML 子集，评分尚未执行代码—知识语义一致性验证，跨进程/跨机器部署也尚未验收。

---

## 12. 完善方案：闭环补齐（2026-08-24）

> 依据 [知识飞轮MVP实现方案评审.md](知识飞轮MVP实现方案评审.md)（7 条潜在问题）。高严重度 3 条（#2 #6 #7）优先补齐，中严重度 2 条（#1 #4）随强评测环落地，低严重度 2 条（#3 #5）当前保持。

### 12.1 补"反馈→修订"闭环（#6，高）

**现状**：§10.7 反馈只回流为 usage 评分；correct 勘误不触发修订。

**完善**：

1. ledger 增加 `pending_corrections` 队列：correct 记录进入队列，附 concept name + 反馈内容 + 时间
2. 新增 revise 流程（CLI 子命令 `fw revise <name>`）：
   - 读 pending_corrections 中的记录
   - 按 sources 反查定位待修订段落（归因，参考 review/attributor 思路）
   - 调 harvester/修订 agent 生成修订版知识卡（draft）
   - 走标准 ingest 管道：评分 → 门禁 → 版本升级（旧版进 history）
3. 修订后的卡 version+1，score 重新计算
4. 验收：提交一条 correct 反馈 → 能生成修订任务 → 修订版进入 drafts/concepts → 评分更新

### 12.2 holdout 机制（#2，高）

**现状**：同一套评分规则反复使用，无 hidden 评测，无法区分真学习与刷分。

**完善**：

1. config.json 增加 `holdout_ratio`（默认 0.2）；按 name 哈希把知识卡分成 train/holdout 两集
2. holdout 集卡不参与 usage 信号回流；评分可读但标记 holdout
3. `fw_eval` 增加 `--holdout` 模式：只报告均值±方差，不写回 score 字段
4. 每累计 N 张卡（默认 20）或每周，用 holdout 集做一次真实能力评估，输出报告
5. 验收：holdout 集与 train 集评分趋势可对比；train 优化导致的刷分在 holdout 上不放大

### 12.3 强评测环：知识→代码还原（#1，中）

**现状**：门禁测知识卡文档质量，不测"知识能否还原代码"。

**完善**：

1. scorer 新增信号 S6 还原度（默认权重 0.15，从其他信号按比例让出）：
   - 有 golden/参考实现：知识卡 → 生成代码 → 与参考对比（测试通过率优先，相似度辅助）
   - 无 golden：差分测试自产（同一组输入对比生成代码与源码行为输出）
2. S6 数据不足时优雅降级（权重分配给其余信号），不阻断入库
3. 验收：对一张含完整可还原逻辑的知识卡，S6 能区分"逻辑完整"与"缺段"

### 12.4 溯源锚点升级（#4，中）

**现状**：sources 以文件+行号为主，代码演进后 traceability decay。

**完善**：

1. OKF sources 支持扩展字段：commit / symbol / ast_hash（可选）
2. 新卡强制要求：至少一个 commit 或 symbol 级锚点（行号仅展示）
3. okf.py 解析器支持新字段；S1 溯源完整性检查覆盖新字段
4. 验收：rename 后的源码，commit/symbol 锚点仍可定位；行号漂移不影响归因

### 12.5 jury 定位明确（#3，低，当前保持）

**保持**：门禁判定纯确定性；jury 若启用，只输出解释/补充建议，不参与 gate 阈值判定（或权重上限 0.10）。

### 12.6 task-adaptive 编排（#5，低，扩展期）

**当前不做**。记录方向：deterministic outer loop 不变，内部按任务复杂度动态选择环节（简单知识卡跳过 jury，复杂卡加依赖分析）。

### 12.7 ablation 实验（#7，高，随验证落地）

**现状**：§11 只有单测与可运行验证。

**完善**：补充最小对照组，评估指标 = holdout 真实能力 / 质量分 / 成本 / 人工介入：

1. harvester 提炼 vs 直接 ingest 原始文件
2. 多信号（7 信号）vs 单信号（仅 S1）
3. runner 管道 vs 直接入库（无评分门禁）

**验收**：三组对比报告，明确各组质量分与成本差异，支撑"组件是否必要"的结论。

### 12.8 落地顺序

1. **P0（下一步直接做）**：12.1 修订闭环 + 12.2 holdout，补全"反馈→修订"半环、防刷分
2. **P1**：12.3 强评测 + 12.4 溯源锚点
3. **P2**：12.7 ablation + 12.5/12.6（简单项）
