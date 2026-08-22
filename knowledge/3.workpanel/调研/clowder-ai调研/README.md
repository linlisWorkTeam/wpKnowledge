# clowder-ai 调研（总览）

> 调研对象：https://github.com/zts212653/clowder-ai（内部名 cat-cafe，"家叫猫咖，品牌叫 Clowder"）
> 快照：2026-08-23 ｜ 数据源：ECS 克隆（depth 30，main）+ GitHub API（stars/forks/releases/tags）
> 定位一句话：**把孤立的 AI agent 变成「真正团队」的本地优先平台层——持久身份、跨模型互审、共享记忆、协作纪律。**
> slogan：*Hard Rails. Soft Power. Shared Mission.* ｜ *Models set the ceiling. The platform sets the floor.*

## 数据速览

| 项 | 值 |
|----|-----|
| Stars / Forks | ≈ 2,707 / 701（2026-08） |
| 建仓时间 | 2026-03-12 ｜ GitHub Releases：v0.1.0 – v0.12.0（约 21 个 tag，节奏先周后月） |
| 技术栈 | TypeScript 5 + pnpm 9 monorepo；Next.js Web（:3003）+ Electron 桌面壳（自带 Node+Redis）；SQLite + Redis |
| 规格规模 | `docs/features/` 294 份 `F###` 功能规格（F001–F300），另有 feature-specs 7 份 |
| Agent 接入 | 不替代 CLI：Claude Code / Codex / Gemini CLI / opencode / Antigravity 等之上的适配层（stream-json/json/AGY/ndjson/ACP） |
| 协作机制 | Threads（隔离工作区）+ @mention 路由 + A2A 异步消息；58 项 cat-cafe-skills；跨模型互审内建 |
| 开源形态 | 内部 cat-cafe 源仓 → 开仓 clowder-ai 单向"清洗同步"出口（sync/* 快照 tag；签 CLA、代码有 TRADEMARK 声明） |

## 五个分项

| # | 主题 | 文档 |
|---|------|------|
| 1 | clowder-ai 原始设计：4+1 视图 / 设计理念 / 竞品优缺 / 演进方向 / 开发笔记 | [01-clowder-origindesign](01-clowder-origindesign.md) |
| 2 | ohMyWorkPanel 与 clowder-ai 到底哪里不同 / 对 clowder 的优势与劣势 | [02-compare-with-ohMyWorkPanel](02-compare-with-ohMyWorkPanel.md) |
| 3 | clowder 的演进方向，ohMyWorkPanel 在其中承担什么（结合 Connecter） | [03-evolution-and-connecter](03-evolution-and-connecter.md) |
| 4 | 作者关注的问题：竞品数量与竞争力 / 未来 / 猫咖 soul 是否可替代 / 商业价值与生态 | [04-authors-concerns](04-authors-concerns.md) |
| 5 | 联合思考：soul 注入、MDI、全互通、孵化产品、开源共享（ohMyWorkPanel 视角） | [05-joint-thinking](05-joint-thinking.md) |

## 三个最关键的事实（先记住再读）

1. **猫就是灵魂**：每只 agent 是一只猫（宪宪·布偶=Claude、砚砚·缅因=Codex、烁烁·暹罗=Gemini……），人格定义在 `cat-template.json`（35KB roleTemplates），"养成系"体验是产品粘性的来源；
2. **平台层不是模型层**：Clowder 明确三层（Model → Agent CLI → Platform），自己只做身份、路由、记忆、互审、SOP 守护——"模型决定天花板，平台决定地板"；
3. **开源仓是"翻译出口"**：内部代码/包名/Redis key 全是 `cat-cafe`（npm scope `@cat-cafe/*`），对外仓库经脱敏脚本同步——理解 clowder-ai 必须同时看它的内部叙事。