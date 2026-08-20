# 笔记：分析过程摘要

- 证据：`gh api` 读 deepseek-harness 文档 + `npm view @deepseek-ai/dsh@0.1.0-rc.6`；未本机全量 install。
- 包规模：~226 packages；CLI ~61 direct deps；Node >=22.19。
- 主机：Mem 1.8Gi（与任务「勿整仓接入」一致）。
- 交付：`docs/dsh-analysis-report.md`
