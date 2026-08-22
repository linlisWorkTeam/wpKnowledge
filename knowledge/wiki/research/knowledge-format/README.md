# 📦 knowledge-format · 知识格式与组织

> 知识形态：解释型 Markdown 知识文档的格式规范与组织方式。
> 按时间排序（最新在前）。

## 📄 文档索引

| 文档 | 类型 | 时间 | 置信度 | 一句话 |
|------|------|------|--------|--------|
| [sok-agentic-skills.md](sok-agentic-skills.md) | 综述 | 2026-02 | 🟡 中 | Agentic Skills 生命周期+7 设计模式（技能=知识形态参考） |
| [cannbot-knowledge.md](cannbot-knowledge.md) | 仓库★ | 持续 | ✅ 高 | 昇腾 NPU 知识库插件（生产/治理/检索/勘误全流程） |
| [knowledge-catalog-okf.md](knowledge-catalog-okf.md) | 仓库★ | 持续 | ✅ 高 | Google OKF 规范：Markdown + YAML frontmatter 知识格式 |

> ★ 两者为**设计核心参考**（docs/overview.md §6 锚点仓库）：OKF 定格式（⭐8756）、cannbot 定运营流程（昇腾官方活跃维护），不受公开仓库 star 门槛约束。

## 📌 核心结论

1. **OKF 格式可直接借鉴**：Markdown + frontmatter（sources/status/verified），知识库天生可信、可 diff、可评审
2. **cannbot 是完整运营样例**：knowledge-query（检索）+ knowledge-lint（门禁）+ ingest（生产），且 frontmatter 用的就是 okf.v1 —— 两个参考仓库是同一体系
3. **知识格式 = 规格**：知识文档足够结构化后可视为规格，Agent 基于它生成代码 = spec-to-code（见 doc-generation/spec2rtl-agent.md）
