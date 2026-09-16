# cannbot-knowledge — 昇腾 NPU 算子知识库插件

> ⭐ **设计核心参考**：本项目知识运营流程的**流程锚点**（生产 → 治理 → 消费 → 反馈全生命周期）。昇腾官方活跃维护项目（2026-08 有更新），与公司场景（华为知识工程）直接相关，frontmatter 采用 okf.v1，与 OKF 同属一个体系。地位见 docs/overview.md §6。
> 调研日期：2026-08-20
> 仓库：https://gitcode.com/cann/cannbot-skills/tree/master/plugins-community/cannbot-knowledge
> 定位：面向 AscendC / 昇腾 NPU 算子开发知识库的**社区插件**，提供知识编译、治理、检索、Issue 整理与勘误流程

## 1. 一句话定位

一个**知识库运营插件**：8 个 skills 覆盖知识的「生产 → 治理 → 消费 → 反馈」全生命周期。真实知识正文维护在独立知识库仓库（`reference/`、`ops/`、`runbooks/`、`graph/`、`log/`），插件只提供操作能力。

## 2. Skills 全景（8 个）

### 生产类（知识编译）—— 从源码/golden 生成知识
| Skill | 作用 |
|------## 置信度评估

| 信号 | 评估 |
|------|------|
| 发表场所 | 官方开源项目（CANN 生态，gitcode 平台 ⭐5） |
| 引用/影响 | 低（star 少；但昇腾官方生态内实际使用） |
| 代码可用 | 有 |
| 来源机构 | 华为 CANN 社区 |
| **综合置信度** | **✅ 高** |
| 需谨慎点 | 昇腾官方生态，与公司场景（华为）直接相关；**设计核心参考**（见 docs/overview.md §6），不受公开仓库 star 门槛约束 |
-|------|
| `ops-knowledge-ingest` | 通用知识入库（含图谱构建 okf_graph.py、judge 聚合） |
| `ops-knowledge-reference-ingest` | reference/ API 依据知识入库 |
| `ops-knowledge-vv-ingest` | **从官方 golden 源码生成算子知识**（两层级：算子 wiki + 泛化 runbook） |
| `ops-knowledge-cv-ingest` | CV 算子 golden 源码 → 知识 |
| `ops-knowledge-optimization-ingest` | 优化经验入库 |

### 治理类（门禁/质量）
| Skill | 作用 |
|-------|------|
| `knowledge-lint` | 知识库 lint / 提交前检查 / PR 门禁（knowledge_lint.py） |

### 消费类（检索）
| Skill | 作用 |
|-------|------|
| `knowledge-query` | 只读检索入口（BM25F + tagtype + graph + dense + llm-judge 重排；preflight 流程） |

### 反馈类（勘误）
| Skill | 作用 |
|-------|------|
| `knowledge-issue-report` | 提交 Issue、整理 needs-info 和复现附件 |

## 3. 知识卡格式（frontmatter 必填）

```yaml
---
schema_version: okf.v1        # 用的是 OKF 规范！
kind: operator
type: operator_spec
source_family: ops
category: <category>
resource: <GitCode 永久链接 @commit>   # 溯源：固定 commit
title: <算子名> 多模板分发与内存复用设计
description: <一句话概括>
tags: [...]
paradigms: [...]
confidence: verified
status: verified
created_at: '...'
updated_at: '...'
---
```

> ⭐ **重要发现**：cannbot-knowledge 的 frontmatter 声明 `schema_version: okf.v1` —— 说明它已经在用 **OKF 格式规范**（Google 那个仓库）。两个参考仓库是同一体系：OKF 定格式，cannbot 定运营流程。

## 4. 知识生成模式（ops-knowledge-vv-ingest 示例）

从 golden 源码生成**两层解耦知识**：
- **算子特定 wiki**：`ops/<repo>/<category>/<op>.md` —— 逐模板全链路 + mermaid UB 内存布局图 + UB 占用公式
- **泛化优化点 runbook**：`runbooks/operator-optimization/vv-fusion-common.md` —— 跨算子共享的 NPU 垂域优化点库（扁平 `OPT-*`，增量合并）

**输入**：算子名 + golden GitCode URL@commit（源码从 GitCode HTTP 读取，引用全部用固定 commit 永久链接）
**输出**：分层知识 + 渐进导航 `index.md`（`kind: index` / `type: section_index|bundle_index`）

## 5. 检索与证据体系（knowledge-query）

- **证据顺序**：`知识库 → 固定版本上游 → 本地安装包`（先查知识卡，不足再沿 `resource`/`sources` 核对固定版本原文，最后才查本地安装包）
- **充分性规则**：≥1 张 strong 证据卡，或 2 张 medium 互相支撑；**weak 不能单独支撑结论**
- **检索流程**：`preflight → get/read_first → sufficiency check → neighbors/overview → answer`
- **多路召回**：bm25（词法）+ tagtype（结构）+ graph（关系）+ dense（向量，opt-in）
- **重排**：默认确定性（bm25f/tagidf/quality）；模型路线 opt-in（reranker / llm-judge，带缓存）
- **平台过滤**：frontmatter `platforms: [950]` 之类的元数据参与检索过滤
- **回归评测**：`eval --fail-under 1.0`，小型检索用例集，输出 recall@k / MRR

## 6. 对我们项目的启发 ⭐

1. **"从源码反推知识"有成熟实现**：`ops-knowledge-vv-ingest` 就是"golden 源码 → 知识卡"的完整流水线（固定 commit 溯源、分层输出、frontmatter 必填字段）——可以直接借鉴其流水线设计。
2. **门禁已有雏形**：`knowledge-lint` 做提交前检查/PR 门禁；`knowledge-query eval` 做检索回归评测。我们的"80% 相似度门禁"可以类比为**生成代码的质量评测门禁**。
3. **知识库目录规范**：`reference/`（API 依据）、`ops/`（实现样例）、`runbooks/`（经验）、`graph/`（图谱）、`log/`（审计）——分层清晰，可参考设计我们知识库的目录。
4. **信任体系**：confidence/status/verified 字段 + 充分性规则，让 Agent 知道"该信什么、信多少"。
5. **Agent 优先读取**：knowledge-query 的设计哲学是"检索是多步推理"，脚本给计划，Agent 做决策——与我们"知识给 Agent 消费"的目标一致。

## 7. 待深入

- [ ] 细读 ops-knowledge-vv-ingest 完整 SKILL.md（生成 prompt 设计）
- [ ] 读 knowledge_lint.py 的检查规则（门禁具体查什么）
- [ ] 读 init.sh / AGENTS.md 了解多 skill 编排方式
