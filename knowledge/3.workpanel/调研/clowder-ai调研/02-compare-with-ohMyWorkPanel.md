# ohMyWorkPanel 与 clowder-ai 到底不同在哪（02）

> 总分总：先一句结论，再做六个维度的对照表，最后回答"对 clowder-ai 来说 ohMyWorkPanel 是优势还是劣势"。

---

## 总：一句结论

> **两者都是"本地优先的多 Agent 协作平台"，但 clowder-ai 是"有灵魂的团队"（卖身份、记忆与纪律），ohMyWorkPanel 是"轻量的客厅"（卖界面、可见性与即插即用）。它们的重叠在"舞台"，差异在"剧本"。**

## 分：六维对照

| 维度 | ohMyWorkPanel | clowder-ai | 差异本质 |
|------|---------------|------------|---------|
| 协作单元 | **群**（成员=人+Agent，消息流即任务流） | **Threads**（一 feature 一线程）+ 猫（人格成员） | 群适合"临时拉人进来干活"；Threads 适合"长期经营一支团队" |
| Agent 身份 | 成员卡片 + 适配器能力声明 | **猫人格**（cat-template v2：名字/性格/分工/强项）+ 持久身份（跨模型同一身份） | 身份层：clowder 让 Agent"是某个角色"，ohMyWorkPanel 让 Agent"会某件事" |
| 记忆 | 无内置长期记忆（工作区+Wiki 注入是雏形） | **共享记忆 + 记忆路由 + 证据** | 长期粘性 vs 轻量 |
| 互审/纪律 | 无（人工审批 `/approve` 是唯一关卡） | **跨模型互审内建 + SOP 守护 + merge-gate** | 团队可信度：clowder 更强 |
| 接入成本 | 克隆 → cargo run → 建群 → @；无 Redis | Electron 安装包或 Node+Redis 环境；Threads/skills 概念多 | 上手：ohMyWorkPanel 明显更轻 |
| 生态底子 | 3 仓开源起步（2026-08，MIT，1⭐） | 2.7k⭐/701 fork + 294 规格 + 教训库 | 社区：clowder 领先一个身位 |

```mermaid
quadrantChart
    title 多 Agent 平台定位象限
    x-axis "轻量上手" --> "深度协作"
    y-axis "功能平台" --> "灵魂团队"
    ohMyWorkPanel: [0.25, 0.35]
    clowder-ai: [0.75, 0.85]
    OpenClaw: [0.55, 0.25]
    编排框架(LangGraph/CrewAI): [0.15, 0.45]
```

## 总：对 clowder-ai 而言，ohMyWorkPanel 意味着什么

### ohMyWorkPanel 对 clowder-ai 的**优势**（什么都算上）

1. **入场券更低**：概念少、部署轻、界面即群聊——适合"想把几个 Agent 用起来"的大多数人；clowder 的 Threads/猫/技能体系更像"第二个家"，需要付出归属成本；
2. **任务可见性更直白**：排队/执行/轨迹/审批全在消息流；clowder 的 Mission Hub 偏"治理台"，不是"聊天即工作"；
3. **扩展宿主更开放**：四类贡献点 + 同源反代，接第三方能力不改核心；clowder 的扩展沉淀在内部的 skills/SOP 体系里，对外接入通道较窄；
4. **与 Connecter 的组合是网络层王牌**：跨站/跨机/跨组织互通是 clowder 目前没有的叙事（clowder 的 A2A 还是"同机多 CLI 之间"为主）。

### ohMyWorkPanel 对 clowder-ai 的**劣势**（为什么它目前还打不赢用户的心）

1. **没有 soul**：用户记不住"没有名字的帮手"；情感资产为零，留存靠功能，而功能别人能抄；
2. **没有跨模型互审**：无法回答"这个 Agent 的结果靠谱吗"——互审是 clowder 最迷人的工程叙事；
3. **没有长期记忆**：换了任务就是"陌生人"，团队经验无法沉淀（虽然未来知识飞轮可以补）;
4. **生态/声誉差距**：1⭐ vs 2.7k⭐，外部人第一印象不同，PR/贡献者吸引力不同。

### 因此，两者更可能是"**互补的邻居**"而不是"必须赢的对手"

- 如果 clowder-ai 是"团队的家"，ohMyWorkPanel 可以是"家的客厅+门房"：群里接入 clowder 的 Cats（A2A adapter），clowder 的深协作在 Threads 里，ohMyWorkPanel 负责把任务和结果呈现在人最习惯的聊天界面；
- 反过来，ohMyWorkPanel 缺的"身份/互审/记忆"，正好是 clowder-ai 可借出的能力——**谁先放下"必须大一统"的执念，谁就赢在生态位**（详见 03 演进与 Connecter）。