# 06 · ohMySocialPanel 能否做成 DSH 插件（补充问题）

日期：2026-08-23
方法：本会话 DSH Inspect Provider 实时取证 + 组织既有先例 + 架构匹配分析

---

## 1. 结论先行

**可行，且组织已有先例与设计预研。** 但"做成 DSH 插件"有两种含义，必须区分：

| 含义 | 定义 | 可行性 | 适配度 |
|---|---|---|---|
| A. 把 ohMySocialPanel 作为 **DSH 宿主内的一项能力（会话/工具/UI 插件）** | DSH 会话中直接提供社交 Agent 交互（角色扮演、情绪陪伴、整活生成），走动态 Cordis 插件 | ✅ 高 | 适合"开发期/内测期/个人使用"，不适合大众分发 |
| B. 把 ohMySocialPanel 作为 **独立消费级产品，但以 DSH 为执行引擎** | 产品外壳独立（Web/App），DSH 作为 agent 循环/工具/持久化后端（headless/ACP/HTTP） | ✅ 高 | 适合对外产品化，即"oyMP 双平面"设计的既有方向 |

两者可以并用：B 是产品的最终形态，A 是快速验证与内部使用形态。**不建议**把大众社交产品做成"只能装在 DSH 里的插件"——DSH 是开发者工具心智，不是普通用户的入口。

## 2. 本会话 DSH 能力取证（Inspect Provider 实时目录）

DSH Host 提供的与"社交 Agent 产品"直接相关的能力（均已有 Service 目录签名，非猜测）：

| 能力 | Service | 用途（对应 SocialPanel） |
|---|---|---|
| Agent 生命周期 | `agentLoop.create / resume`、`agents` | 为每个社交角色创建独立 Agent 会话 |
| 持久会话 | `sessionPersistence`（append-only、可回放） | 聊天记忆、角色关系历史（"心不可换"的资产） |
| 子代理编排 | `subagents.start / startContinuable / followup` | 多角色群聊：主持人 + 陪聊 + 整活分工 |
| 动态工具注册 | `tools.register` + harness Builtin | 社交技能：梗图生成、玄学抽牌、情话生成等以 Tool 暴露给 Agent |
| HTTP 服务 | `webServer.register` | 对外 API（如 `/social/chat`），供第三方/前端调用（先例：/fw/query） |
| LLM 多路适配 | `llm`（adapter registry + stream） | 多模型角色（不同人格配不同模型/温度），`llm/stream` waterfall 可注入人格前缀 |
| 定时驱动 | `timer`（inject） | 主动陪伴（问候、睡前故事、每日塔罗） |
| 事件总线 | `Event`（session/event、agent/inbox/*、workflow/*） | 消息唤醒、进度通知、回放 |
| 沙箱与 shell | `sandbox` / `shell` / `subprocess` / `fs` | 内容产物的文件落地与外部调用（图像/音频生成脚本） |
| 前端 Slots/Theme | Client `Slots` / `Theme` | 在 DSH Web 界面内做聊天/角色面板（开发期用） |
| 工作流引擎 | `workflowEngine` | 批量剧本/互动流程编排 |

## 3. 组织既有先例（最重要证据）

1. **知识飞轮已做成 DSH 动态插件**：`endlessWpKnowledgeRunner/dsh/fw-plugin.js`（本会话正在运行）验证了完整套路：
   - Host 插件 `inject: ['timer']` + `ctx.get('shell'|'subagents'|'webServer'|'sandboxPolicy')`；
   - 注册 10 个模型 Tool（fw_*）+ HTTP 端点 `/fw/query`；
   - liveMode 用 timer 驱动 + subagent 做 harvester；
   - 生命周期 = 当前 DSH 进程，可停可删（cordis_stop / cordis_undefine）。
   → **ohMySocialPanel 插件可以完全复用这一工程模板**（tools + webServer + subagents + timer），只是把"知识提炼"换成"社交互动"。

2. **组织已设计 DSH 双平面**：ohMyWorkPanel 的 `dsh-self-bootstrap` 设计把 DSH 定位为"执行/创造平面"（agent 循环、工具、可回放会话、可逆注册、能力 seam），并已交付 P0（headless dsh CLI 适配器 + 跳转 DSH Web 内嵌 :3080）。**这意味着"DSH 作为社交 Agent 执行引擎"不是新想法，而是组织架构路线的一部分。**

3. **wpKnowledge 仓库本身跑在 DSH 上**：本调研就是 DSH 会话 + 知识飞轮 + wpKnowledge 协作的实例——组织已惯用"DSH 插件 + 独立仓库"的开发模式。

## 4. 做成 DSH 插件的具体方案建议（含义 A）

```text
pluginId: ohMySocialPanel（host-only 起步）
  apply(ctx):
    - 注册 Tool：osp_chat（与角色对话）/ osp_roles（列出角色）/ osp_spell（生成整活内容）
    - harness.handle('social/chat', ...) 供 Client 调用（若做 UI）
    - webServer.register('GET /osp/chat', ...) 对外 API
    - timer：每日问候/晚安（可选）
    - subagents：多角色群聊时按角色 spawn 子代理
  角色 = 数据（persona JSON：名字/头像/性格提示词/模型偏好），存知识库或 settings
```

- 角色人格注入点：`llm/stream` waterfall 或 `systemPrompt.section()`（给每个角色会话挂独立 prompt section）——这正好对应组织"可替换 soul 内核"的设计理念。
- 关系记忆：`sessionPersistence` append-only + `sessionQuery` 检索——"心不可换"的资产落地。
- 验证周期：与知识飞轮相同，`cordis_define`（new，idPrefix 如 `ospl`）→ `cordis_run` → 本会话工具目录出现 osp_*。

## 5. 限制与风险

1. **进程生命周期**：动态插件随 DSH 进程存活，重启需重载；对外产品必须另有常驻载体（含义 B）。
2. **单会话作用域**：插件能力绑定当前 Agent 会话（工具对当前模型可见），大众用户的"人人可用"需要走 HTTP 端点 + 独立前端（webServer 已有路由注册能力，可做）。
3. **不直接拥有消费者 UI**：Client 插件的 Slots 是在 DSH Web 里，面向开发者/内测；大众 UI（移动端/小程序/H5）仍需独立产品壳。
4. **资源与计费**：DSH 侧没有用户账户/计费体系，商业化需在独立壳层做。
5. **心智错位**：把"娱乐产品"锚定在"开发者 harness"上会限制传播——建议插件只是开发与内部形态，对外始终是独立产品。

## 6. 结论

- 含义 A（DSH 插件形态）：**可行、低成本、有先例**，适合快速验证"社交 Agent 玩法"或做内部工具/社区尝鲜版。
- 含义 B（DSH 当执行引擎的独立产品）：**可行、是组织既定路线**（dsh-self-bootstrap 设计），也是可规模化路径。
- 最终建议：**先插件验证玩法（一周级），再独立产品化**；插件与产品共用同一角色/记忆 schema，保证资产可迁移。