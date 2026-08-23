# 市场调研：soul 加载概念图谱（问 1）

> 快照 2026-08-23。结论先行：**市面不但有 soul 加载的概念，而且已经卷到了"开放标准 + 全生命周期 + 三条制造流水线"的完整生态**。omp 不是第一个吃螃蟹的人，而是"要选哪只螃蟹"的人。

---

## 1 · 直接叫"soul"的：术语已经成立

| 项目/标准 | 是什么 | soul 的样子 | 证据 |
|---|---|---|---|
| **soulspec**（clawsouls） | "AI agent persona 的开放标准：一个文件、持久身份" | 一个 soul 包 = `soul.json`（元数据）+ `SOUL.md`（核心人格）+ 可选 `IDENTITY.md` / `AGENTS.md` / `STYLE.md` / `HEARTBEAT.md` / 头像 / 校准样例；v0.5 已支持机器人具身 | [GitHub](https://github.com/clawsouls/soulspec)、[Spec Overview](https://docs.clawsouls.ai/docs/spec/overview/)、[v0.6 草案](https://docs.clawsouls.ai/docs/spec/v0.6/) |
| **SOUL.md 文件标准** | 多个独立仓库同时提出"给 agent 一份 SOUL.md" | [soul.md RFC-1](https://raw.githubusercontent.com/rokoss21/soul.md/main/README.md)、[soul-spec（AntonioTF5）](https://github.com/AntonioTF5/soul-spec)、[aaronjmars/soul.md](https://github.com/aaronjmars/soul.md) | 网页快照 |
| **@neomei/agentsoul** | "Give OpenCode a soul——人格注入 + 长期记忆" | 直接在编码 agent 上挂 soul | [npm](https://www.npmjs.com/package/@neomei/agentsoul) |
| **OpenPersona** | agent 无关的人格生命周期框架（4+5+3） | persona.json + state.json + soul/ 注入件；支持 create/install/switch/uninstall/fork/export/import/publish/contribute 全命令 | [GitHub](https://github.com/acnlabs/OpenPersona) |
| **AgentOS Soul Files** | 每 Agent 一个 Markdown 灵魂工作区（SOUL/STYLE/IDENTITY/AGENTS/MEMORY/examples 六文件），启动时按序加载 | 支持 HEXACO 人格分 + mood overlay + 人格漂移机制 | [docs](https://docs.agentos.sh/features/soul-files) |
| **OpenClaw soul 概念** | 桌面/网关级 agent 平台的 soul 工作区（SOUL.md/AGENTS.md/HEARTBEAT.md 等） | [概念文档](https://github.com/openclaw/openclaw/blob/fbdf5937/docs/concepts/soul.md)、[SOUL.md 指南](https://openclaw.cc/en/concepts/soul) | 网页快照 |
| **clowder-ai cat-template.json** | 我们调研过的猫咖：每只猫 id/昵称/头像/配色/角色/性格/团队强项 | 猫 = soul 的具体形象化 | [01-clowder-origindesign](../../调研/clowder-ai调研/01-clowder-origindesign.md) |

**判断**：soul 一词已不是 clowder 的私有概念，而是 2025–2026 年 agent 生态里的通用术语，且正处**竞争定义期**：soulspec（v0.6 仍是草案）、soul.md、soul-spec、AgentOS SOUL_FILES、OpenPersona 在平行竞争"标准格式"。这意味着 omp 若自造格式，将错过生态红利；**但"兼容谁"是候选策略而非既定结论**——建议采用"抽象字段层 + soulspec 作为默认导出目标"，保留切换余地（详见 09 章兼容性决策与 07 章 P0 验收）。

## 2 · 不叫 soul 但机制同构的

| 机制 | 代表 | 与 soul 的对应 |
|---|---|---|
| **角色卡（Character Card）** | SillyTavern CCv2/CCv3：单文件定义人格+示例对话，可导入/导出/切换/社区分发 | 最成熟的人格加载载体，CCv3 甚至带 lorebook | [SillyTavern](https://github.com/SillyTavern/SillyTavern)、[角色管理](https://deepwiki.com/SillyTavern/SillyTavern/5.1-characters-and-chat-storage) |
| **仓库级人格约定** | AGENTS.md / CLAUDE.md / .cursorrules：随仓库携带"这个项目里 agent 是谁、怎么干活" | 文件级 soul，编程场景事实标准 | [Tembo 讲解](https://www.tembo.io/blog/agents-md)、[Devin Rules](https://docs.devinenterprise.com/cli/extensibility/rules) |
| **平台级记忆人格** | ChatGPT 记忆 + 自定义指令（记住你是谁、怎么跟你说话） | "常驻人格"的平台实现，跨会话生效 | [OpenAI 帮助](https://help.openai.com/en/articles/11146739-how-does-reference-saved-memories-work)、[官方教程](https://learn.chatgpt.com/docs/personalize) |
| **用户自创角色市场** | Character.AI：数千万级用户自创角色（平台自述口径，无官方精确统计，未见公开财报细分），人人可创建/分享 | "soul 商店"的商业验证（陪伴赛道头部） | [Character.AI 指南](https://www.codaone.ai/blog/character-ai-complete-guide-2026/) |
| **人格注入 npm 包** | 给编码 agent 注入人格 + 长期记忆 | 一键给 agent "装灵魂"的最小实现 | [@neomei/agentsoul](https://www.npmjs.com/package/@neomei/agentsoul) |

## 3 · 生态已经出现的完整闭环（soul 生命周期）

OpenPersona 的 README 把 soul 的完整生命周期摆得很清楚（快照 03b924f）：

- **声明→生成→安装→运行→进化→卸载→携带**：`create`（声明 persona.json 自动补全）→ `install`/`switch` → 运行时 `state-sync` 状态持久化 + Soul Evolution（带 `immutableTraits` 边界约束、可回滚快照）→ `uninstall`/`export`/`import`（zip 携带）→ `fork`（从父人格派生子人格）→ `contribute`（把本地改进回灌上游）。
- **三条"造 soul"的生产线**（细节见 05/06 章）：`persona-seed`（从人口语料采样）、`anyone-skill`（从聊天记录蒸馏）、`persona-knowledge` + `persona-model-trainer`（知识库 + 本地微调模型）。
- **质量与安全门禁**：soulspec 配套 `soulscan`（安全/质量扫描）、`validate`、`test`（schema/行为测试）与发布注册表；OpenPersona 有 Generate/Install/Runtime 三道门。

**评定**：soul 加载概念 = 已成熟。对 omp 的启示：**我们进入的不是一个空白市场，而是一个"格式标准正在收敛、生产流水线已经开源、商店模式已被 Character.AI 验证"的市场**——最适合的打法是"兼容 + 场景化"，把生态现成物收编进 omp 的群聊形态，而不是重造轮子。

## 4 · 一句话回答

> 有，且有标准、有全生命周期框架、有三条开源生产线、有被验证的商店模式。omp 的问题从"做不做 soul"变成了"接哪个标准、挂哪个层级、用哪条生产线"——这正是后面各章回答的。