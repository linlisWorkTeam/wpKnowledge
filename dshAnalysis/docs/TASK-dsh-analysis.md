# 任务：DeepSeek Harness（dsh）可借鉴性分析报告

## 背景
LinlisWorkPanel 是多 Agent 群聊编排平台（Rust 调度 + 外挂 CLI：Cursor/Codex/OpenClaw…）。
[deepseek-ai/deepseek-harness](https://github.com/deepseek-ai/deepseek-harness)（`dsh`）是 Cordis 插件式 **agent harness**（开发者预览）。
**不要**把整仓 dsh 接入本机常驻（1.8G 内存机上 `npm i @deepseek-ai/dsh` 安装峰值 ~820MB 仍未完成）。

## 目标
产出一份**分析报告**（Markdown），路径建议：
`/AI/dshAnalysis/docs/dsh-analysis-report.md`

报告须回答：
1. dsh 模块拆解（core/session、system-prompt、tools、goal/plan、compaction、permission、headless、MCP…）
2. 与 WorkPanel 能力对照：哪些**概念可借鉴**、哪些**不要搬**
3. 对 WorkPanel 的落地优先级（高/中/低）与建议切片（尤其 Context Seams / Handoff / run 事件日志）
4. 性能与资源风险（安装体积、RSS、与现有 Agent 并行）
5. 明确结论：能否作为与 Cursor/Codex **平级适配器**；若仅借鉴机制，推荐路线是什么

## 约束
- 工作目录：`/AI/dshAnalysis`（可在此写笔记与报告；勿改 `/AI/LinlisWorkPanel` 生产代码，除非报告里只提建议）
- 优先读 GitHub 文档/包结构；本机勿大规模 `pnpm install` 整仓
- 最终在群内用简短结论回复，并指出报告文件路径
