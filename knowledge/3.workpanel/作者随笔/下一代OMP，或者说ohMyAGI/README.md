# 下一代 OMP，或者说 ohMyAGI · 随想

> 前置调研：ohMyWorkPanel（omp）未来 soul 功能的专题调研。起因是 clowder-ai 的 soul（猫猫）主张"人格化能留人"（clowder 作者信念，无公开留存数据，需 omp 对照实验验证），我们需要判断 omp 要不要做 soul、做到什么层级、怎么造出来。
> 快照日期：2026-08-23。调研方式：公开资料（web）+ 一手仓库取证（git clone 阅读源码/文档）。

## 一句话结论

> **soul 已经不是"要不要做"的问题，而是"接轨哪个标准、挂到哪个层级、用哪条生产线造"的问题**——市面正在竞争定义人格格式（soulspec 当前最完整候补、仍是草案），soul 应挂到**群文化 + 成员个性**两层，以"上下文前缀注入"为壳、以"身份/记忆分层"为常驻机制、以**预制群组（SoulFactory）和长期对话蒸馏**两条生产线造 soul，并在建群时做默认推荐。形态与接线在 01–15 章中均有标记"待验证"的假设清单。

## 七问速览

| # | 问题 | 短答 | 详见 |
|---|------|------|------|
| 1 | 市面上有 soul 加载的概念吗？ | **有，而且已经卷成标准**：soulspec（开放人格包标准）、SOUL.md/AGENTS.md（文件级）、OpenPersona（全生命周期）、SillyTavern 角色卡、AGENTS.md 工程约定、ChatGPT 记忆/自定义指令、clowder cat-template 等 | [01 市场调研](01-市场调研：soul加载概念图谱.md) |
| 2 | 加载到哪个层级？加载后怎么常驻？ | **群文化 + 成员个性两层绑定**；接入时绑定、会话启动注入、运行中热切换；常驻 = 配置常驻 + 注入常驻 + 记忆常驻（身份/经验分层）+ 活性常驻 | [02 设计：加载层级、常驻与一键卸载](02-设计：加载层级、常驻与一键卸载.md) |
| 3 | 支持一键卸载？ | **必须支持，而且有现成机制可抄**：OpenPersona switch/uninstall + 上下文移交、soulspec restore 回退、soul 资产可导出带走（clowder 教训：关系资产不可回收） | [02 设计：加载层级、常驻与一键卸载](02-设计：加载层级、常驻与一键卸载.md) |
| 4 | 加载哪些 soul？场景推荐？建群预制？ | 工程角色类（评审/架构/文档/测试/安全/PM）对开发收益最高；场景类、文化类（MBTI 首发）、陪伴/导师类、品牌类兜底；**建群时按群用途推荐 + 预制群组下发** | [03 设计：soul 类型、场景推荐与建群预制](03-设计：soul类型、场景推荐与建群预制.md) |
| 5 | soul 是下一版 top 吗？ | **不是全局 top1，但是体验层 top1**。全局先做 Connecter 生产化 + A2A/MCP 服务器面（总机牌）；soul 与它们隔离良好、成本低，可并行先行发布 | [04 判断：soul 在下一版本的优先级](04-判断：soul在下一版本的优先级.md) |
| 6 | 能流水线制造 soul 吗？需要预制群组吗？ | **能**。预制群组 = 灵魂生产线（采集/提炼/门禁/发布四角色），复用知识飞轮的门禁与打分机制；代价主要是内容工程而非代码 | [05 制造：流水线生产 soul 与预制群组](05-制造：流水线生产soul与预制群组.md) |
| 7 | 能长期对话归纳 soul 吗？ | **能**，且是成本最低的生产线：聊天记录 → 周期蒸馏 → 人工确认门 → soul 包；业界有 anyone-skill 全流程与 MDR 记忆蒸馏研究背书 | [06 制造：长期对话归纳 soul](06-制造：长期对话归纳soul.md) |
| 8 | soul 在 ohMyAGI 中的概念位置？ | **第一类实体**：绑身份不绑进程（跨站 soul）、记忆与身份分离、壳不碰电梯、生产线自举——从"管 agent"到"养 agent"的概念跃迁 | [08 概念：soul 在 ohMyAGI 中的位置](08-概念：soul在ohMyAGI中的位置.md) |
| 9 | 首发怎么落地？ | 12 个 SKU 字段草案 + 建群推荐映射表 + 入库门禁（soulscan 53 模式、最低 C 级） | [09 设计：首发 soul 货架与建群推荐参考](09-设计：首发soul货架与建群推荐参考.md) |
| 10 | 猫咖的猫怎么入伙？ | **一键迁移协议**：cat-template v2 一手取证（f2b9c118），soul=breed 与 body=variant 分离、mentionPatterns/互审策略/硬边界全映射；import/export 双向 | [10 兼容：clowder 猫咖的猫如何一键入伙](10-兼容：clowder猫咖的猫如何一键入伙.md) |
| 11 | 生产线群模板长什么样？ | SoulFactory 预制群组：采集/提炼/评审/发布四角色 + 工单状态机 + 五道门禁（复用飞轮） | [11 设计：SoulFactory 预制群组模板](11-设计：SoulFactory预制群组模板.md) |
| 12 | soul 怎么保证可靠？ | **评测体系（总纲）**：静态五信号（结构/溯源/安全/去重/时效）+ 动态四信号（跨模型保真/对话内一致性/召唤可靠/价值反馈）+ verified/draft/gated 三级门禁 + 评测卡上墙 | [12 评测：soul 的可靠性评测体系](12-评测：soul的可靠性评测体系.md) |
| 13 | soul 怎么变成生意？ | **合规红线**（国内深度陪伴收紧 → 工作人格定位）+ 三层货架（官方免费/社区分享/精选付费）+ 权限骑 Connecter 身份（默认拒绝、变更留痕） | [13 生态：soul 商店的经济模型与治理权限](13-生态：soul商店的经济模型与治理权限.md) |
| 14 | soul 与 DSH 怎么合流？ | **soul = DSH 与 omp 的人格交换格式**：persona 行即 SOUL.md 宿主；`soul2dsh` / `dsh2soul` 双向导出（取证 linlis-super-harness 预设） | [14 合流：soul × DSH 的 agent-preset 映射](14-合流：soul×DSH的agent-preset映射.md) |
| 15 | 对外怎么讲？ | 介绍稿（草稿）："值得共事的队伍"叙事 + 评测/合规口径红线 | [15 对外：ohMyAGI 与 soul 介绍稿](15-对外：ohMyAGI与soul介绍稿.md) |
| 16 | 假设怎么验证？ | **预注册 P0 对照实验**：A 注入 / B 无 soul / C 皮肤安慰剂三组，30 天留存主指标、判定阈值写死、结果联动路线升降级 | [16 验证：soul 假设的 P0 对照实验设计](16-验证：soul假设的P0对照实验设计.md) |
| 17 | ohMyAGI 的主目标是什么？ | **两大方向**：①给 agentTeam 赋予 souls（1–16 章体系收拢）②humanlike 主动式交互（19 章骨架）；与 04/07 章优先级衔接 | [17 愿景：ohMyAGI 的两大主目标](17-愿景：ohMyAGI的两大主目标.md) |
| 18 | 业界怎么定义 AGI？ | 定义谱系（OpenAI 五级/DeepMind 性能×泛化矩阵/METR 量化/中文语境）+ **八项特性清单**；策略：不做 AGI，做"团队协作相关"子集（自主性/社交智能/持续学习/对齐） | [18 调研：业界如何定义 AGI 与 AGI 特性](18-调研：业界如何定义AGI与AGI特性.md) |
| 19 | humanlike 主动式交互怎么做？ | **四层主动性（汇报→提醒→提问→行动）× 打扰预算（自适应/忽略回流）× 人设风格（soul.proactivity）× 真实数据与审计**；落地 P1 心跳并入既有路线 | [19 设计：humanlike 主动式交互](19-设计：humanlike主动式交互.md) |

> 概念已入飞轮：`omp-soul` 知识卡 score 93.0，verified，v2（2026-08-23 交叉评审后修订入卡；`knowledge/concepts/omp-soul.md`。注：机器评分，未含独立评审；usage 信号缺位）。
>
> **交叉评审记录**：2026-08-23 由独立评审视角通读全套后出具意见书（A 内部矛盾 10 条 / B 薄弱假设 9 条 / C 过度自信 6 条 / D 遗漏 10 条 / E 可执行性 5 条）。已按高→低优先级修订：统一 SKU 口径（全量 12 / P0 首发 8）、门禁总纲归位 12 章、注入优先级与 CLI 注入矩阵、P0/P0a/P0b 拆分与本地审计先行、跨站记忆列为 P2.5 新组件、`clowder-import` 首批 6 猫口径、"人格化能留人"降级为待验证假设、soulspec 兼容降级为候选策略（验收= `clawsouls validate` 通过）、MBTI 商标注、评测分层出资、商店运营最小流程等。评审意见书全文与修订对照未随库保存（如需可重跑评审）。

## 落点建议（详见各章）

1. **格式**：不发明新格式——取 soulspec 结构（`soul.json` + `SOUL.md`/`IDENTITY.md`/`AGENTS.md` 精简子集），保留 clowder cat-template 的迁移映射。
2. **层级**：soul 绑定在 Group（团队气质）与 Agent（成员个性）两层；注入点为上下文前缀 + 群公告/成员卡片；**soul 是壳，不是电梯**，不碰任务状态机。
3. **常驻**：身份（T0 不可变）与经验（T1/T2 分层、可衰减、可晋升）分开存；意识与记忆分离，防"记忆-身份悖论"。
4. **卸载**：一键解绑 + 停止注入 + 资产导出；切换带上下文移交（handoff）。
5. **制造**：P0 预制模板商店（含建群推荐）→ P1 对话蒸馏生产线 → P2 流水线（SoulFactory 预制群组）+ 社区回灌。
6. **验证**：用跨模型保真度思路给 soul 打分评测（soul 也有"可靠性"问题），可挂进现有知识飞轮评测体系。

## 一手证据来源

| 来源 | 快照 | 用途 |
|---|---|---|
| [soulspec（clawsouls）](https://github.com/clawsouls/soulspec) | `569cbd1` 2026-07-27 | 开放人格包标准：包结构/CLI/四层记忆/ swarm |
| [OpenPersona（acnlabs）](https://github.com/acnlabs/OpenPersona) | `03b924f` 2026-08-11 | soul 全生命周期框架：create/install/switch/uninstall/fork/publish + 进化边界 + 三条制造流水线 |
| [anyone-skill](https://github.com/acnlabs/anyone-skill) | 同上仓库内 | 对话/资料 → 4 维人格提取 + L1-L4 证据分级 → 可运行 persona 包 |
| [AgentOS SOUL_FILES](https://docs.agentos.sh/features/soul-files) | v0.9.26 | 每 Agent Markdown 灵魂文件 + 启动加载顺序 + HEXACO |
| [OpenClaw soul 概念](https://github.com/openclaw/openclaw/blob/fbdf5937/docs/concepts/soul.md) 与 [SOUL.md 模板画廊](https://openclawcheatsheet.com/gallery) | 网页快照 | 36+ 现成人格模板、角色模板（PM/Dev/QA/Security/Lead） |
| [SillyTavern 角色卡](https://github.com/SillyTavern/SillyTavern) | 网页 | 角色卡（CCv2/CCv3）生态：导入/导出/切换 |
| [AGENTS.md 工程约定](https://www.tembo.io/blog/agents-md) | 网页 | 仓库级人格/行为约定成为编程 Agent 事实标准 |
| [ChatGPT 记忆与自定义指令](https://help.openai.com/en/articles/11146739-how-does-reference-saved-memories-work) | 网页 | 平台级"记住你"机制 |
| [MDR 记忆蒸馏论文](https://www.sciencedirect.com/science/article/abs/pii/S0950705125022865)（Knowledge-Based Systems 336, 2025） | 网页 | 对话 → 个性化人格蒸馏的学术背书 |
| [Cross-Model Persona Fidelity](https://zenodo.org/records/18849974)（2026-03） | 网页 | 结构化身份文件跨模型保真评测——soul 的"可靠性评测"先例 |
| clowder-ai 猫咖调研（本知识库） | [clowder-ai调研](../../调研/clowder-ai调研/README.md) | 猫人格 cat-template、soul=留存杠杆 |
| Connecter P0-P3 实施状态（本知识库） | [Connecter P0-P3实施状态](../../规划/Connecter%20P0-P3实施状态.md) | omp 当前 roadmap 基线 |

> 仓库 clone 与网页均只做只读取证，未改动任何上游与个人账号数据。