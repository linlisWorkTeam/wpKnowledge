# wpKnowledge
wp输出的知识库

## Repository boundaries

- `endlessWpKnowledgeRunner/` contains the flywheel implementation, CLI, DSH adapter, Dashboard, and tests.
- `knowledge/` contains the controlled OKF knowledge base: four curated knowledge domains (`dshAnalysis/`, `wiki/`, `workpanel/`, `workpanelConnecter/`) plus `inbox/` for new candidates, `drafts/` for below-gate cards, `concepts/` for verified cards, `history/` for protected versions, and `runtime/` for governance state.
- New knowledge enters through `endlessWpKnowledgeRunner/fw.py ingest`; agents must not write cards directly into `knowledge/concepts/`.

The layout and insertion contract are documented in [`knowledge/README.md`](knowledge/README.md) and [`endlessWpKnowledgeRunner/docs/KNOWLEDGE-REPOSITORY.md`](endlessWpKnowledgeRunner/docs/KNOWLEDGE-REPOSITORY.md).

## Knowledge domains

The following directories are knowledge content, not executable projects. They
are intentionally kept under `knowledge/` so the flywheel can cite, review,
score, and version them as one knowledge bundle:

### dshAnalysis

DeepSeek Harness（dsh）可借鉴性分析（WorkPanel 机制样本，非整仓接入）。

- 报告：[`knowledge/dshAnalysis/docs/dsh-analysis-report.md`](knowledge/dshAnalysis/docs/dsh-analysis-report.md)
- 拆解调查：[`knowledge/dshAnalysis/docs/2026-08-20-dsh-disassembly-investigation.md`](knowledge/dshAnalysis/docs/2026-08-20-dsh-disassembly-investigation.md)
- 白话图文版：[`knowledge/dshAnalysis/docs/2026-08-20-dsh-plain-illustrated.md`](knowledge/dshAnalysis/docs/2026-08-20-dsh-plain-illustrated.md)
- 插件化拆解：[`knowledge/dshAnalysis/docs/2026-08-20-dsh-pluginization.md`](knowledge/dshAnalysis/docs/2026-08-20-dsh-pluginization.md)
- 插件化（专业技术版）：[`knowledge/dshAnalysis/docs/2026-08-20-dsh-pluginization-professional.md`](knowledge/dshAnalysis/docs/2026-08-20-dsh-pluginization-professional.md)
- 任务书：[`knowledge/dshAnalysis/docs/TASK-dsh-analysis.md`](knowledge/dshAnalysis/docs/TASK-dsh-analysis.md)
- 过程笔记：[`knowledge/dshAnalysis/notes/2026-08-14-analysis-notes.md`](knowledge/dshAnalysis/notes/2026-08-14-analysis-notes.md)

### wiki

研究索引、知识格式、飞轮设计和候选池：[`knowledge/wiki/`](knowledge/wiki/)

### workpanel

LinlisWorkPanel 架构、竞品、技术选型与演进建议知识库。

- 综合报告：[`knowledge/workpanel/docs/workpanel-analysis-report.md`](knowledge/workpanel/docs/workpanel-analysis-report.md)
- 2.0.0 架构评审：[`knowledge/workpanel/docs/2026-08-21-workpanel-architecture-review.md`](knowledge/workpanel/docs/2026-08-21-workpanel-architecture-review.md)
- 任务书：[`knowledge/workpanel/docs/TASK-workpanel-analysis.md`](knowledge/workpanel/docs/TASK-workpanel-analysis.md)
- 调研笔记：[`knowledge/workpanel/notes/2026-08-21-analysis-notes.md`](knowledge/workpanel/notes/2026-08-21-analysis-notes.md)
- 修改建议复评：[`knowledge/workpanel/docs/2026-08-21-workpanel-followup-review.md`](knowledge/workpanel/docs/2026-08-21-workpanel-followup-review.md)

### workpanelConnecter

WorkPanelConnecter 的设计理念、演进路线、市场竞品与跨平台连接研究。

- 综合报告：[`knowledge/workpanelConnecter/docs/workpanel-connecter-analysis-report.md`](knowledge/workpanelConnecter/docs/workpanel-connecter-analysis-report.md)
- 设计与路线：[`knowledge/workpanelConnecter/docs/2026-08-22-design-and-evolution.md`](knowledge/workpanelConnecter/docs/2026-08-22-design-and-evolution.md)
- 竞品分析：[`knowledge/workpanelConnecter/docs/2026-08-22-competitive-analysis.md`](knowledge/workpanelConnecter/docs/2026-08-22-competitive-analysis.md)
- Clowder 集成分析：[`knowledge/workpanelConnecter/docs/2026-08-22-clowder-integration-analysis.md`](knowledge/workpanelConnecter/docs/2026-08-22-clowder-integration-analysis.md)
