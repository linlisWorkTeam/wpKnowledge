# 📄 doc-generation · 代码文档生成（源码 → 知识）

> 飞轮第一步：如何从源码反推解释型 Markdown 知识文档。
> 按时间排序（最新在前）。

## 📄 文档索引

| 文档 | 类型 | 时间 | 置信度 | 一句话 |
|------|------|------|--------|--------|
| [repodoc.md](repodoc.md) | 论文 | 2026-04 | ⚠️ 谨慎 | 知识图谱驱动文档生成+变更传播 |
| [llm-agents-see-repos.md](llm-agents-see-repos.md) | 论文 | 2026-06 | 🟡 中 | 让 agent 感知仓库结构（视觉/文本） |
| [remember-your-trace.md](remember-your-trace.md) | 论文 | 2026-05 | 🟡 中 | 记忆引导长时程生成，保证跨文档一致 |
| [reporepair.md](reporepair.md) | 论文 | 2026-03 | 🟡 中 | 分层文档用于程序修复（文档质量的间接验证） |
| [spec2rtl-agent.md](spec2rtl-agent.md) | 论文 | 2025-06 | 🟡 中-高 | 规格→硬件代码（NVIDIA，严格规格有效） |
| [knowledge-graph-codegen.md](knowledge-graph-codegen.md) | 论文 | 2025-05 | ⚠️ 谨慎 | 知识图谱 + 混合检索增强代码生成 |
| [docagent.md](docagent.md) | 论文 | 2025-04 | 🟡 中 | 5 Agent 协作生成（Reader/Searcher/Writer/Verifier） |
| [llm-api-docs.md](llm-api-docs.md) | 论文 | 2025-03 | 🟡 中 | ⚠️ 文档注入对 LLM 帮助有限（知识格式警示） |
| [repoagent.md](repoagent.md) | 论文+仓库 | 2024-02 | ✅ 高 | 仓库级文档生成框架：拓扑序 + 增量更新 |

## 📌 核心结论

1. **生成顺序**：按依赖拓扑序，先生成依赖对象（repoagent/docagent 一致验证）
2. **分层文档**：函数级 + 文件级两层抽象，被 reporepair 验证有效
3. **上下文组织**：全局结构（Project Tree/依赖图）+ 按需检索，避免塞爆上下文
4. **一致性**：记忆/索引机制保证跨文档不矛盾（remember-your-trace）
