# 03 · workpanel 架构与定位分析：ohMySocialPanel 站在哪里

日期：2026-08-23
对象：linlisWorkTeam 组织（4 仓库：ohMyWorkPanel / workpanelConnecter / wpKnowledge / ohMySocialPanel）

---

## 1. 先厘清"workpanel"指什么

用户问题 3 中的"workpanel"在本调研语境下指 **linlisWorkTeam 组织自有的整套 Agent 平台架构**，即：

| 组件 | 职责 | 技术形态 | 已有知识来源 |
|---|---|---|---|
| ohMyWorkPanel（原 workPanel，v2.1.1） | 多 Agent 群聊协作面板（治理/协作平面） | Rust + SQLite + Tauri/Web + React 19 | `3.workpanel/` |
| workpanelConnecter（v0.2.3+） | 跨站点/跨机联邦网络层 | JavaScript（Node），Site/Host 拓扑 | `4.workpanelConnecter/` |
| wpKnowledge（本库） | 知识飞轮（沉淀/评测/检索） | Python + OKF + DSH 插件 | `2.wiki/`、`knowledge/` |
| ohMySocialPanel（新） | *Agent For Social*——社交向 Agent 面板（推断） | 空仓，仅有 README | 本次调研 |

**结论性判断**：ohMySocialPanel 不是"另一个 WorkPanel"，而是 WorkPanel 生态在**社交/娱乐方向**的新产品入口。命名对称（ohMyWork ↔ ohMySocial）与副标题"Agent For Social"都指向：同一套多 Agent 内核，面向"社交场景"（陪伴、娱乐、情绪价值、社区互动）重新包装。

## 2. ohMyWorkPanel 架构事实（4+1 视图摘要，来自已有知识）

- **场景**：群里 @Agent 派活 → 调度器排队 → 本机 CLI 执行 → 状态/输出回流消息流；语音（PanelLive）、外部平台接入（扩展宿主/A2A）。
- **逻辑**：表现层（React 群聊 UI，七主题）→ 应用层（Web API + /ws 事件 + 斜杠命令决策卡 + Workflow）→ 领域层（群/消息/运行状态机/身份密钥）→ 适配层（CLI 适配器目录 + JSON-lines 解析）→ 扩展层（ROOTS 发现、同源反代）+ SQLite。
- **进程**：`ohmyworkpanel-server`（:8080 生产 / :8081 灰度）↔ CLI 子进程（串行、取消/重试）↔ 扩展进程（PanelLive :8790）↔ Codex 代理 shim。
- **开发**：Rust 后端约 37 模块 + React 前端；发布门禁 51+ 项；扩展代码禁止进平台仓。
- **物理**：本地优先（SQLite 落本机），ECS 灰度/生产双槽位，root 人工批准 promote。

**架构本质**（与 DSH、Clowder 对比后的一句话）：**它是一个"以群聊为治理平面、以外部 Agent CLI 为执行平面、以状态机为骨架"的多人多 Agent 协作平台**。强在治理与可见性，弱在"运行时自举原语"（回放、可逆 effect、能力 seam）——后者正是 DSH 的长处，也是组织已设计"ohMyWorkPanel + DSH 双平面"互补的原因。

## 3. 组织演进脉络（推断 ohMySocialPanel 的位置）

```text
workPanel（本地多 Agent 面板）
  → ohMyWorkPanel v2.0/v2.1（改名 + 微信风壳层 + 七主题 + 扩展宿主 + DSH 适配）
  → workpanelConnecter（跨站联邦，Site/Host 拓扑，本地优先不变量）
  → wpKnowledge（知识飞轮：让 Agent 沉淀可复用知识）
  → ohMySocialPanel（Agent For Social —— 面向"社交/娱乐"的产品化出口）  ← 本调研对象
```

关键佐证（来自已有知识与源码）：

1. **战略文档已预告**：`06-strategy-thinking.md` 命题 2/4 明确提出"情绪价值付费 → soul"与"孵化产品"（AI 协作文档连载 / 主题皮肤商店 / 多 Agent 互动剧本），并指出"情绪价值天花板最高的方向是直接对标猫咖的陪伴经济"。ohMySocialPanel 的命名与副标题与该命题高度吻合。
2. **"轨道 D 聊天群"已在平台内存在**（`docs/version-pipeline.md` 轨道 D + v1.3 已实现的 `groupKind=chat`）：不绑定工作区、允许多 chatbot、默认响应者、chatbot 窗口上下文（12 条/8k 预算）、v2.1 微信式对话手感——并明确"不做朋友圈/已读/赞踩"。→ 说明**社交聊天形态是 ohMyWorkPanel 已验证的能力**，ohMySocialPanel 极可能将其剥离为独立社交产品。
3. **AIHotel（AI 酒馆）扩展已在灰度试运行**：剧本/NPC/好感度业务在扩展仓（`:8791`），平台只提供扩展宿主；战略文档提到"AI 酒馆已在 ECS 灰度群试运行过"。"多 Agent 互动娱乐"（桌游/剧本杀式群活动）被列为情绪价值天花板最高的方向（命题 4 方向 C）。
4. **DSH 自举设计已预研**：`docs/superpowers/specs/2026-08-16-dsh-self-bootstrap-runtime.md` 确立了"治理平面（群聊）+ 执行平面（DSH 运行时）"双平面架构、两级自举执行者（bootstrap-dsh / linlis-super-harness）、以及 P0 "headless dsh CLI 适配器 + 跳转 DSH Web 内嵌"已交付。
5. **soul 概念已有参照**：clowder-ai（猫咖）证明"人格化养成"是产品粘性来源（皮可换、骨难换、心不可换），其"可替换 soul 内核"讨论正是 ohMySocialPanel 这类社交产品要复用的机制设计。

## 4. ohMySocialPanel 定位推断（三角推断，非事实）

因仓库为空，以下为推断，标注置信度：

| 维度 | 推断 | 置信度 |
|---|---|---|
| 产品形态 | 面向社交/娱乐场景的 AI 面板：AI 朋友/伴侣/群聊娱乐 Agent，可能是 Web 端或桌面端（平台内已有聊天群 + AI 酒馆雏形） | 高（命名 + 副标题 + 轨道 D + AIHotel） |
| 目标人群 | 普通消费者（C 端），非开发者 | 高（"Social" vs "Work"） |
| 核心能力 | 人格化 Agent（soul）+ 群聊/1v1 互动 + 情绪价值内容生成 + 可能的多 Agent 娱乐玩法（剧本杀/桌游/陪伴） | 中（组织已有能力 + 战略命题） |
| 底座 | 复用 ohMyWorkPanel 内核或 DSH 运行时之一，或两者组合 | 中（DSH 双平面设计已存在） |
| 商业模式 | 订阅/角色皮肤交易/单次付费（情绪价值经济） | 中（对应战略命题 2/4） |
| 与 DSH 关系 | 可能做成 DSH 插件形态（本调研补充问题），或独立产品 + DSH 执行平面 | 待 06 报告展开 |

## 5. 对四个调研问题的接应

- 问题 1（娱乐类 AI 平台）：ohMySocialPanel 将进入"AI 陪伴/娱乐互动"赛道——该赛道形态/架构/市场的全景见 `01-娱乐类AI平台市场调研.md`。
- 问题 2（情绪价值 TOP10）：ohMySocialPanel 最可能承接的正是这批"简单又搞笑"的情绪价值产品类型（AI 朋友、AI 玄学、AI 整活、AI 剧本）——见 `02-情绪价值AI产品TOP10.md`。
- 问题 3（workpanel 作为发动机）：ohMyWorkPanel + Connecter + 知识飞轮的组合能否批量生产这类产品——见 `04-workpanel作为产品发动机.md`。
- 问题 4（可行性）与补充问题（DSH 插件）——分别见 `05-可行性分析.md`、`06-DSH插件化可行性.md`。

## 6. 证据边界

- ohMySocialPanel 空仓（2 commit，README 仅一行），以上定位推断基于组织命名、战略文档与竞品格局，非源码事实。
- ohMyWorkPanel 架构描述来自本知识库 `3.workpanel/`（基线 c9cceff/v2.0.0）与本轮 `_tmp_ohMyWorkPanel`（主干 v2.1.1）核对，两者一致。
- Connecter 描述来自 `4.workpanelConnecter/`（基线 8b176cb/v0.2.3）。