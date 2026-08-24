# knowledge-catalog / OKF — Google Cloud 知识目录

> ⭐ **设计核心参考**：本项目知识格式的**格式锚点**（⭐8756，活跃维护）。地位见 设计/项目概述.md §6；格式落地见 设计/知识形态定义.md §5。
> 调研日期：2026-08-20
> 仓库：https://github.com/GoogleCloudPlatform/knowledge-catalog
> 核心产出：**Open Knowledge Format (OKF) v0.2 规范** —— 通用、厂商中立的**知识表示格式**

## 1. 一句话定位

OKF 是一套**知识格式规范**，而非某个具体系统：用「纯 Markdown 文件 + YAML frontmatter」表示知识，目录树组织。它的口号是：**能 `cat` 就能读 OKF，能 `git clone` 就能分发 OKF**。

## 2. 核心设计（OKF v0.2）

### 2.1 基本单位
- **Knowledge Bundle**：一捆自包含、层级组织的知识文档（= 一个目录树 / git 仓库）
- **Concept**：一个知识单元 = 一个 `.md` 文件（可描述表、API、指标、业务流程等）
- **Concept ID** = 文件路径（去掉 `.md`）

### 2.2 Bundle 结构
```
bundle/
  index.md        # 目录索引（渐进式披露：逐层导航，不用一次全加载）
  log.md          # 更新历史
  <concept>.md    # 概念文档
  <subdir>/
    index.md
    <concept>.md
```

### 2.3 Frontmatter 是信任核心
OKF v0.2 把以下信号做成 first-class：

| 字段 | 含义 | 解决什么问题 |
|------## 置信度评估

| 信号 | 评估 |
|------|------|
| 发表场所 | 官方开源项目（Apache 2.0） |
| 引用/影响 | 中（Google 官方） |
| 代码可用 | 有 |
| 来源机构 | Google Cloud |
| **综合置信度** | **✅ 高** |
| 需谨慎点 | 官方规范项目，格式设计稳健，可直接借鉴 |
|------|--------------|
| `sources` | 知识来源（每源带可信度信号 author/usage_count/last_modified） | **Provenance 溯源** |
| `generated` / `verified` | 谁生成、谁确认 → 派生信任层级 | **Trust 信任** |
| `status` / `stale_after` | 是否仍有效、何时过期 | **Freshness 新鲜度** |
| `resource` | 上游永久链接（可带 @commit sha） | **Lifecycle 生命周期** |
| `type: Attested Computation` | 知识携带可验证的计算方式（executor + receipt + attester） | **Attestation 可验证性** |

> **关键洞察**：`sources` 记录「来源事实」而非「结论」，信任由消费方从信号推断（unverified / machine-confirmed / human-reviewed 三级）。

### 2.4 参考 Agent（知识生产示范）
两遍式生成知识：
- **BQ pass**：仅用 BigQuery 元数据为每个概念写 1 份 OKF 文档
- **Web pass**：LLM 当爬虫，从 seed URL 出发，判断外链是否值得追，逐页选择 (a) 丰富已有概念 / (b) 新建 references 文档 / (c) 跳过；带 `--web-max-pages` 上限和同域白名单

### 2.5 可视化
`visualize` 子命令把 bundle 渲染成**自包含 HTML 图**：力导向图（概念节点 + 交叉链接边）+ 详情面板 + 反向引用（Cited by）+ 搜索。

## 3. 对我们项目的启发 ⭐

1. **知识格式可直接借鉴**：Markdown + YAML frontmatter 的目录树，正好契合我们"解释型 Markdown 知识文档"的形态；frontmatter 承载 `sources`（溯源）、`status`（新鲜度）、`verified`（信任层级）——知识库天生可信、可 diff、可评审。
2. **Attested Computation = 门禁雏形**：知识文档可以声明"如何验证自己"（executor + attester），确定性代码检查 receipt 返回 verdict。这和我们"Agent 基于知识生成代码 → 与源码对比 → 打分"的门禁机制是同构的。
3. **渐进式披露**：`index.md` 逐层导航适合上亿行代码切出的海量知识文档，避免一次加载全部。
4. **图状知识**：概念间用 markdown 链接表达关系（非仅目录父子），支持知识图谱导航。

## 4. 待深入

- [ ] 细读 SPEC.md 的 Attested Computation 章节（§10），理解 executor/attester 接口设计
- [ ] 看 samples/bundles 里真实 OKF 文档的样子
- [ ] 评估 OKF frontmatter 字段能否直接用于我们的知识卡设计
