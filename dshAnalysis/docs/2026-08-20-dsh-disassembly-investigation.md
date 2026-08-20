# 【拆解DeepSeek Harness】DeepSeek Harness到底做了什么？

| 项 | 内容 |
|---|---|
| 对象 | [deepseek-ai/deepseek-harness](https://github.com/deepseek-ai/deepseek-harness)（`dsh`，开发者预览） |
| 对照 | Clowder-AI、Claude Code、LinlisWorkPanel |
| 证据 | 上游架构/子系统文档、`@deepseek-ai/dsh-llm-deepseek` README、Clowder 公开 README、WorkPanel 本机只读；**未**本机全量安装 dsh |
| 日期 | 2026-08-20 |
| 关联 | 机制借鉴版：[`dsh-analysis-report.md`](./dsh-analysis-report.md) |

---

## 0. 一句话

**DeepSeek Harness 不是「又一个聊天机器人」，而是一套以 Cordis 插件为轴的开源 agent 运行时（harness）**：把会话日志、提示词组装、工具流水线、模型流式适配、审批/沙箱、压缩、目标/计划等拆成可替换能力，再按 profile 组装成 Web UI 或无头一次性 runner。相对 Claude Code 的「成品编码 CLI」、Clowder/WorkPanel 的「多 Agent 编排平台」，dsh 站在**单 agent 内核可组合**这一层。

---

## 1. DeepSeek Harness 到底做了什么？

### 1.1 产品动作（用户能感知）

| 入口 | 行为 |
|---|---|
| `dsh web` / `--profile web` | 启动浏览器侧 Harness UI，在本地跑完整 agent 循环 |
| `dsh --profile headless "task"` | 无 Host/HTTP：建会话 → 提交一条任务 → 等静默 → **stdout 打最终助手文本**后退出 |
| `dsh plugin …` | 按 profile 管理树外插件（pnpm 转发） |

底层依赖 **Node 22.19+ / 24+**、庞大的 `@deepseek-ai/dsh-*` 包树；官方定位为 **开发者预览**，允许破坏性变更。

### 1.2 系统动作（工程上真正交付的）

1. **驱动一轮 agent loop**：inbox → turn/step → 组装 system prompt + tools → `llm/stream` → 工具执行 → 事件入账 → 可续跑/可停。
2. **以仅追加会话事件为唯一真源**：模型历史从日志派生；强调「模型可见即已记录」。
3. **用 Capability Seams 替换能力**：fs/shell/llm/approval/compaction/subagent… 各自 Definition + Provider + Consumer。
4. **用 Profile + Bundle 组装产品面**：`dsh-base` 打底，再叠 web 或 headless，再叠用户 `cordis.patch.yml`。

一句话：**做「可插拔的智能体操作系统内核」**，而不是只做「调一次 DeepSeek Chat API 的 SDK」。

---

## 2. 架构

### 2.1 分层示意

```text
┌─────────────────────────────────────────────────────────┐
| 产品面：apps/cli（dsh）· Web UI · headless runner         |
├─────────────────────────────────────────────────────────┤
| 组装：Profile → Bundle 栈 → cordis.patch / --patch        |
├─────────────────────────────────────────────────────────┤
| Cordis 插件树（一切皆插件，副作用可撤销）                    |
|  ┌──────────┐ ┌────────────┐ ┌─────────┐ ┌────────────┐ |
|  | session  | | system-    | | tools   | | agent-loop | |
|  | 事件日志  | | prompt     | | 把关流水线| | turn/step  | |
|  └──────────┘ └────────────┘ └─────────┘ └────────────┘ |
|  ┌──────────┐ ┌────────────┐ ┌─────────┐ ┌────────────┐ |
|  | llm seam | | compaction | | goal/   | | approval/  | |
|  | +adapters| | / token    | | plan    | | sandbox    | |
|  └──────────┘ └────────────┘ └─────────┘ └────────────┘ |
|  ┌──────────┐ ┌────────────┐ ┌─────────┐                |
|  | MCP/skill| | subagent/  | | fs/shell| …              |
|  | jobs …   | | workflow   | | PTY …   |                |
|  └──────────┘ └────────────┘ └─────────┘                |
└─────────────────────────────────────────────────────────┘
```

仓库为 pnpm monorepo，包数量约 **200+**；发行面以 `@deepseek-ai/dsh` CLI 拉齐默认组合。

### 2.2 运行时主循环（概念）

```text
turn/start
  → agent/pre-step（可改写/拒绝输入）
  → step/start → assemble prompt+tools
  → agent/request → llm/stream → assistant/chunk* → assistant/message
  → tool/call* → tools/pre-execute → execute → post-execute → tool/result*
  → step/end （欠工具或有下一条输入则再 step）
  → agent/turn-stopping
turn/end
```

三类扩展点：

- **会话事件**：持久事实（回放/UI/遥测同源）
- **agent/\***：进行中拦截与续跑
- **能力事件（fs/\*、tools/\*…）**：策略与适配器挂钩

### 2.3 关键子系统速览

| 子系统 | 角色 |
|---|---|
| session | 仅追加 `SessionEvent`；历史派生 |
| system-prompt | 提示词片段与工具 schema 注册组装 |
| tools | 作用域注册 + 把关执行瀑布 |
| llm | `StreamChunk` 协议 + 多适配器路由 |
| compaction | 可选压缩 seam（事件锁 + surface replace） |
| goal / plan-mode | 同会话目标与计划协作态 |
| approval + permission-presets + sandbox | 审批 fail-closed；预设捆绑沙箱×审批 |
| headless / web | 两种产品组装，而非两套内核 |
| MCP / skill / subagent / jobs | 工具生态与委派 |

---

## 3. 设计理念

| 理念 | 含义 | 工程后果 |
|---|---|---|
| **Everything is a Plugin** | Cordis 驱动；无特权「打补丁内核」 | 扩展=并排挂载；卸载撤销副作用 |
| **Capability Seams** | 能力=接口声明 + 提供方 + 消费方一起设计 | 换远程沙箱可连带搬迁 Bash/PTY/LSP |
| **事件溯源会话** | 日志是真源；「模型可见即已记录」 | 新模型输入必须新增可重建事件 |
| **可替换循环** | 消费方依赖 `agent`，不直接绑死 `agent-loop` | loop 可被演示/替代实现替换 |
| **组装优于单体** | profile/bundle/patch 分层 | 同一 core 出 web 与 headless |
| **默认失败关闭（安全相关）** | 审批无应答 → `unavailable` → 拒绝 | headless 常用 `approval/never` 明确无人值守姿态 |
| **开源 harness，官方模型优先但不锁死** | 自研 `llm-deepseek`，另有 `llm-pi-ai` 多提供方 | 可同树挂载多条 DeepSeek 路由 |

论文背景指向 Cordis 的时空可组合范式；产品叙事则是：**把 agent 产品拆成可审计、可替换、可回放的插件图**。

---

## 4. 与底层 DeepSeek API 的适配程度

### 4.1 适配位置

官方直连适配器：`@deepseek-ai/dsh-llm-deepseek`。

- 挂在 **LLM seam**（`ctx.llm`），提供方路由名 **`deepseek-official`**（刻意区别于 pi-ai 目录里的 `deepseek`，以便同组合双挂）。
- 实现路径：**`fetch` + SSE**（`eventsource-parser`），把官方 Chat Completions 线格式译成 harness 内部 **`StreamChunk`**。
- 文档声明以官方 API 文档为线格式真源：thinking mode、tool_calls、create-chat-completion 等指南。

### 4.2 适配深度（评估）

| 维度 | 程度 | 说明 |
|---|---|---|
| Chat Completions / 流式 | **高** | 一等公民；SSE → StreamChunk |
| Tool calls | **高** | 与 tools 流水线对接；官方 tool_calls 指南为参考 |
| Thinking / reasoningEffort | **高（产品向）** | 配置默认 `thinking: enabled`，`reasoningEffort` 可选 |
| 模型目录 | **中高** | 默认可广告 V4 Flash/Pro；**未登记 model id 仍可透传** |
| 多模态图像 | **中（可选开启）** | 默认可不广告 vision；可配 `inputModalities: [text,image]`，经 attachments 转 `image_url`；有 payload 上限与省略策略 |
| 凭据 | **标准** | `DEEPSEEK_API_KEY` / `apiKeyEnv`；走 `ctx.credentials` 再回落环境变量 |
| baseURL | **可配置** | 默认 `https://api.deepseek.com`，可 `$DEEPSEEK_BASE_URL` |
| 重试 / 超时 | **产品级** | 可配 retryPolicy、streamIdleTimeout（默认 5min） |
| 上下文窗口元数据 | **部署可调** | 默认 context 提示约 1M；供 compaction 等压力插件使用 |
| 非 Chat 类 API（若有专用端点） | **未作为本报告重点** | 适配器叙事围绕 chat-completions + 流式工具协议 |

**结论：** 对 **DeepSeek 官方 Chat Completions（含 thinking / tools / 可选视觉）** 是**一等、深度适配**；但 Harness **整体并不等于 DeepSeek API SDK**——API 只是 `ctx.llm` 上的一条提供方。另有 `llm-pi-ai` 走库封装多提供方，说明「模型线」可替换，「agent 操作系统」才是主体。

### 4.3 与「套一层 OpenAI 兼容代理」的差别

WorkPanel/Codex 常见路径是：CLI ↔ OpenAI 兼容网关 ↔ DeepSeek。  
dsh 的 `deepseek-official` 路径是：**Harness 内部词汇 ↔ 官方线格式直译**，并显式处理 thinking、重试、图床省略等产品语义——适配面更深，但也绑定 Node/Cordis 运行时成本。

---

## 5. 四方对比

> 比较的是**层级角色**，不是「谁刷题更强」。

| 维度 | **DeepSeek Harness** | **Claude Code** | **Clowder-AI** | **LinlisWorkPanel** |
|---|---|---|---|---|
| 定位 | 开源 **单 agent harness / 内核** | Anthropic **成品编码 Agent CLI** | **多 Agent 团队协作平台**（CLI 之上） | **群聊编排平台**（Rust + 外挂 CLI） |
| 核心问题 | 如何可组合、可回放、可替换地跑一个 agent | 如何把 Claude 变成强力本地编程助手 | 如何让多个异构 CLI 当「团队」协作 | 如何在群里 @成员、调度、交接、灰度发布 |
| 运行时 | Cordis 插件树 + Node | 闭源/产品化 CLI（用户侧） | Node 平台 + Redis 等；**不替代**底层 CLI | Tauri/Web + Rust scheduler + SQLite |
| 模型关系 | 官方 DeepSeek 深度适配 + 可挂其它 LLM | 绑定 Claude 家族体验 | 多模型：Claude/Codex/Gemini/opencode… | 模型在成员 CLI 内；平台管适配器契约 |
| 扩展模型 | 插件 / seam / patch | 产品扩展点（相对封闭） | Skills、SOP、MCP 桥、插件仓 | AdapterKind、Extension Host、A2A、epitaph |
| 多 Agent | subagent/jobs（同 harness 内） | 主打单助手（产品内可有委派，但非「猫群」叙事） | **一等**：身份、A2A、互审、共享记忆 | **一等**：群成员、提及路由、同 Agent 串行队列 |
| 会话真源 | 仅追加 SessionEvent | 产品自有会话/resume | 平台记忆 + 各 CLI 会话 | DB messages/runs + epitaph 人读交接 |
| 无人值守 | headless profile | CLI 非交互/权限模式（产品自有） | 平台编排 + 各 CLI 权限 | 调度 spawn CLI；权限多在 CLI/沙箱策略 |
| 开源可控 | MIT harness，可读可改 | 产品主导 | MIT 平台开源 | 自有仓，可改调度与适配器 |
| 资源画像 | 依赖闭包大；弱机安装风险高 | 用户本机已装 CLI 则平台侧轻 | 桌面/源码 + Redis，偏「整屋」 | 1.8G 双槽位约束下强调轻适配器 |

### 5.1 关系一句排比

- **Claude Code**：把「编程 agent」做成**最好用的单一工具**。
- **DeepSeek Harness**：把「编程 agent」拆成**可重组装的操作系统**，并深度接 DeepSeek API。
- **Clowder-AI**：假定你已有 Claude/Codex/…，解决**多猫协作、身份与纪律**。
- **WorkPanel**：假定你已有多种 CLI，解决**群聊调度、发布与交接**；与 Clowder 同属「平台层」，叙事更偏内部运维/工作流而非桌面猫咖。

### 5.2 对 WorkPanel 的启示（不重复长文）

优先借鉴 dsh 的 **Seams / 事件日志 / Compaction / Goal / Permission 预设**；**不要**把 Cordis 整仓嵌进 1.8G 生产机。与 Clowder 的相似点是「CLI 之上的编排」；差异是 WorkPanel 已用 Rust 调度 + 灰度双槽，扩展应沿 Adapter/Extension，而非再引入第二套 Node 协作运行时。

---

## 6. 未来发展方向思考

### 6.1 上游 dsh 可能走向（观察 + 推演）

1. **预览 → 稳定**：插件契约与 SessionEvent 词汇冻结；降低「跟版本税」。
2. **官方模型能力同步**：thinking / 长上下文 / 视觉 / 工具协议随 DeepSeek API 演进，`llm-deepseek` 会持续当「参考适配器」。
3. **Seam 生态**：更多沙箱提供方、远程执行世界、编辑器 ACP 集成；`dsh-plugin` 话题聚拢第三方。
4. **headless / SDK 产品化**：对 CI 与外部编排更友好的稳定 stdout/JSON 契约（今天已有 one-shot 文本契约雏形）。
5. **风险**：若始终保持巨型 Node 单体，则难以进入边缘/弱主机编排场景。

### 6.2 行业分层收敛（判断）

```text
模型 API  ←  harness 内核（dsh / 各厂 runtime）  ←  单产品 CLI（Claude Code / Codex）
                                              ←  多 Agent 平台（Clowder / WorkPanel）
```

长期更可能是：**平台选 CLI，CLI 内嵌或外挂 harness 机制**；而不是所有平台都自研完整 Cordis 树。

### 6.3 WorkPanel 可落地方向（建议）

| 优先级 | 方向 | 说明 |
|---|---|---|
| 高 | Run 事件日志 + Context Seams | 对齐「模型可见即已记录」；服务 Experience/Logs 与回放 |
| 高 | Handoff（epitaph）运行时注入桥 | 人读 SSOT → 可审计注入事件 |
| 中 | Compaction / Goal 轻量态 | chatbot 窗口与 Wave 续跑 |
| 中 | Permission 预设字段 | 群/成员级策略命名，执行仍可交给 CLI |
| 低 | `AdapterKind::Dsh` | 仅隔离机验证 headless 资源与契约后；生产默认关闭 |
| 避免 | 整仓 Cordis / 常驻 `dsh web` | 与内存门禁、双槽位发布冲突 |

### 6.4 若问「该不该押注 dsh 替代 Claude Code？」

**不该。** 二者层级不同：Claude Code 赌的是编码体验与生态；dsh 赌的是可组合内核与 DeepSeek 官方线对齐。平台侧更合理的押注是：**吸收 dsh 的机制，继续把 Claude Code / Codex / Cursor 当劳动力，把 WorkPanel 当工头。**

---

## 7. 风险与证据边界

| 风险 | 说明 |
|---|---|
| 开发者预览 | API/插件语义可能破坏性变更 |
| 资源 | 弱机全量安装曾出现数百 MB 峰值仍失败；不宜与生产 Agent 并行常驻 |
| 对比信息 | Clowder/Claude Code 依据公开文档与定位，非逐行源码审计 |
| DeepSeek API | 适配结论基于 `llm-deepseek` 文档与架构说明，非本机联调抓包 |
| 未改生产代码 | 本报告仅文档输出 |

---

## 8. 结论

DeepSeek Harness **做的是**：用 Cordis 插件图实现可组装、可回放、可替换的 **agent 操作系统**，并对 **DeepSeek 官方 Chat Completions（含 thinking/tools 等）做深度一等适配**。  
它**不是** Claude Code 的直接替代品，也**不是** Clowder/WorkPanel 这类多 Agent 群聊平台的替代品；三者叠层互补。  
对 WorkPanel：**抄机制、不搬整仓**；用事件日志与 Context Seams 把「工头」做厚，继续用成熟 CLI 当「工匠」。
