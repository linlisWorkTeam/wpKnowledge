# 【拆解DeepSeek Harness】插件化机制专业技术报告

> Host / Client 双面运行时、组装契约与扩展点  
> 2026-08-20 · 对读白话调研稿：[2026-08-20-dsh-pluginization.md](./2026-08-20-dsh-pluginization.md)

| 项 | 内容 |
|---|---|
| 范围 | Cordis 插件运行时；Profile/Bundle 组装；Host 服务/事件；Client `dsh.client` 启动图；动态扩展 |
| 证据 | 上游 `docs/cordis-primer`、`architecture`、`client-modules`、`web-server`、`extensions`、`bundle/{base,web-app}`、cookbook |
| 方法 | 文档与包契约分析；未在本机启动 `dsh web` 做 HMR 实操 |
| 版本锚点 | `@deepseek-ai/dsh@0.1.0-rc.6` 量级（开发者预览） |

---

## 1. 问题定义

「插件化」在 dsh 中不是 UI 扩展市场，而是：

> **产品的每一可观察能力（模型适配、工具、会话日志、agent loop、审批、压缩、Web 路由、Chat 节点……）都是 Cordis 插件，经由配置树组装，注册为可逆副作用。**

需要同时回答三个工程问题：

1. **Host（Node）** 如何发现、依赖排序、挂载与卸载插件？  
2. **Client（浏览器）** 如何在不共享 Node 运行时的前提下，装载对应的 UI 半？  
3. **两面** 如何用同一组合配置对齐，而不共享可变全局单例？

---

## 2. 运行时模型

dsh 将 Cordis 作为 vendor 框架。插件不是「调用方 import 实现」，而是向 **共享 Context** 贡献服务与事件。

```mermaid
flowchart TB
  subgraph compose [Composition]
    P[Profile]
    B[Bundles: dsh-base → dsh-web-app | dsh-headless]
    X[profile / home / --patch overlays]
  end

  subgraph host [Host process · Node]
    L[Loader + include]
    CTX["ctx.&lt;key&gt; services"]
    EV[typed events]
    WS[ctx.webServer]
    CM[ctx.clientModules]
  end

  subgraph client [Browser]
    BOOT["window.__DSH_BOOT__"]
    PJ["GET /plugins/&lt;id&gt;/client.js?rev="]
    UI[ConversationNode / slots]
  end

  P --> B --> X --> L --> CTX
  CTX --> EV
  CM --> WS
  CM -->|tapIndex| BOOT
  CM -->|named route| PJ
  BOOT --> PJ --> UI
```

**不变量：** `web` 与 `headless` 是同一 Host 内核的两种 **surface bundle**，不是两套插件框架。`dsh-web-app` 只在 base 之上插入 HTTP、client roster、HMR 与 `web-runtime`。

---

## 3. Cordis 契约（Host 插件化的宪法）

### 3.1 五个原语

| 原语 | 契约 |
|---|---|
| Plugin | 带 `inject` + `apply(ctx)` 的函数，或 `Service` 子类 |
| Context | 稳定 `ctx.<key>` 服务容器；消费方按 key 查找，不 import 实现包 |
| `inject` | 声明服务依赖；Loader 等依赖就绪再激活，启动序由依赖图表达 |
| Events | 声明合并注册事件名；分发模式是公开约定的一部分 |
| Reversible effects | `ctx.effect()` / `ctx.on()`；teardown / reload 必须撤销注册 |

### 3.2 事件分发模式

| 模式 | await | 语义 | 典型用途 |
|---|---|---|---|
| `emit` | 否 | 观察、无返回 | 审计、遥测 |
| `waterfall` | 否 | `(...args, next)` 中间件；不 `next()` 即短路 | `agent/pre-step`、`tools/pre-execute`、`approval/request` |
| `parallel` | 是 | 扇出 | 无返回的并行观察 |
| `serial` | 是 | 顺序、有返回 | `agent/turn-stopping` |

Waterfall 是策略插入的主表面：协作监听器修改共享决策对象后委托；拥有决策权的监听器可短路。`prepend: true` 仅在必须早于普通注册时使用。

### 3.3 Loader 与配置插值

`@deepseek-ai/cordis-plugin-include` 将 `!!js` 解析为表达式节点。条目 `config` 在声明的 inject 激活后，于插件上下文插值；`disabled` 在每次挂载决策时基于 loader 上下文插值。环境选择插件应使用 overlay，而不是在代码里硬编码启动序。

**实践规则：** 工具流水线事件属 `ctx.tools`，模型流式属 `ctx.llm`，实时协调属 `ctx.agents`。拦截走事件；直接能力走服务方法。每个注册必须有 disposer。

---

## 4. 组装层：Profile / Bundle / Patch

### 4.1 叠加顺序

```text
empty root
  → each bundle patch in dsh.profile.bundles order
  → profile cordis.patch.yml
  → $DSH_HOME/cordis.patch.yml
  → --patch overlays
```

- **`dsh-base`**：每个 profile 第一层；插入模型适配、agent-default-model、工具、持久化、策略、凭据、遥测、默认 subagent。包本身无 runtime API，composer 只读 `dsh.bundle.patch`。  
- **`dsh-web-app`**：叠 webserver、API gateway、workspace、projection cache、browser plugin roster、`dsh-client-hmr`、`web-runtime`。  
- **`dsh-headless`**：兄弟 surface，不挂 Host/HTTP/浏览器。

Patch **按 id 整行替换 config**（非深合并）。模式相关默认值必须写在 mode bundle。平台门控示例：同一份 patch 用 `disabled: !!js process.platform === 'win32'` 在 bash / pwsh 两套 shell 栈中二选一；不完整覆盖会在 load 时 fail-loud（例如双注册 `ctx.fs` 或同一 `bash` 服务）。

### 4.2 包拓扑与 Host/Client 编译面

普通包 **恰好属于一个 TypeScript aggregate**：`tsconfig.host.json` 或 `tsconfig.client.json`，禁止双属。`packages/client/*` 使用 `tsconfig.base.client.json`。

Capability 若独立演化，拆成 **Service Definition / Provider / Consumer** 三包（shell 三件套为模板）。`ctx` key 命名：单数=一台引擎/策略/store；复数=registry。Host 与 Client **不得复用同一 Context key 声明不兼容类型**——declaration merging 会同时看见两面。

---

## 5. Host 插件如何扩展产品

一个 Host 包的典型贡献面：

| 贡献 | 机制 | 例 |
|---|---|---|
| 占据服务 | `ctx.<key>` | `ctx.sessions`、`ctx.compaction` |
| 注册提供方 | seam registry | `ctx.llm` ← `deepseek-official` |
| 注册消费方 | tools / systemPrompt | `dsh-tool-bash`、prompt sections |
| 策略 | waterfall / serial | approval fail-closed；`unavailable` ≠ 放行 |
| 持久词汇 | `SessionEventMap` declaration merging | `compaction/*`、`goal/*` |
| HTTP | `ctx.webServer.register` / `tapIndex` | `/plugins/*`、index manifest |

**Capability Seam**：替换 Provider 必须让所有 Consumer 仍正确（远程沙箱同时搬迁 Bash / PTY / LSP）。这是插件化的「深度」指标：扩展点在能力边界，而非单个工具 fork。

### 5.1 Web 载体故意无业务语义

`dsh-host-webserver`：`node:http` 插件，提供 `ctx.webServer`。匹配序固定：exact → 最长 prefix → 唯一 fallback owner。它不理解 harness 概念。`/api`、client bundle、HMR SSE 均由其他插件注册。`tapIndex` 按序转换每个 index 响应；`dsh-client-modules` 用它注入启动图。Electron 走 `file://` + IPC，不使用该服务器。

这把 **「能开端口」** 与 **「有哪些插件路由」** 解耦：HTTP 插件化 = 路由表上的可逆注册。

### 5.2 动态 Cordis（上限形态）

`ctx.dynamicCordisRunner`：会话内 define / undefine 带版本的 Cordis 包，运行 Host 半生命周期。  
`ctx.cordisInspect`：Host/Client provider 目录与跨面 query。  
仍受沙箱与会话所有权约束；不是任意 `eval`。

---

## 6. Client 插件化：声明、启动图、投递

Client 不是独立插件框架。它是 **同一组合树中带浏览器半的包**，由 Host 扫描并投递。

### 6.1 进入启动图的条件

1. `package.json` 声明 `dsh.client`（`platform: 'web'`；可选 `inject`、`immediately`）  
2. `exports["./client"]` 指向构建 bundle（共享 tsdown client preset）  
3. 包解析锚定 `ctx.baseUrl`（cordis.yml 目录）；未设置则构造抛错  

`ctx.clientModules`（`ClientModuleRegistry`）扫描 Loader entry。扫描为 **单包增量**：`internal/plugin` 将 entry 标脏，微任务 flush 对账。激活期畸形声明 → `AggregateError` 且 fiber FAILED；稳态损坏包只警告、不株连。包元数据（含「非 client」否定结论）按名缓存，变更需重启。

### 6.2 Wire：`WebBootGraph` 为唯一真源

Host 组合 `WebBootEntry[]`，作为 `<head>` 第一脚本注入 `window.__DSH_BOOT__`（`<` 转义，防 script breakout）。图缺失或畸形 → 浏览器解析器 fail-loud。

```ts
interface WebBootEntry {
  id: string              // == package name
  url: string             // '/plugins/<id>/client.js?rev=<rev>'
  rev: string             // bundle content hash
  inject?: string[]       // informational edges
  immediately?: boolean   // stage-one prefetch / factory registration
  external?: string[]     // constrains code arrival (sync require)
}

interface WebBootGraph {
  rev: string             // hash of composed rows
  entries: WebBootEntry[] // module-graph order ≠ Cordis activation order
}
```

- 行 `rev` 作 cache-bust query；图 `rev` 覆盖任一行变化。  
- `immediately`：模块面启动时 fetch+执行，仅登记。惰性行首次 import 才拉。  
- `external` 约束代码到达；`inject` 仅预检/HMR diff。  
- Cordis fiber 等待与 client 模块图顺序 **解耦**。

### 6.3 投递与 HMR

- `GET/HEAD /plugins/<id>/client.js`：`no-cache` 读盘；未知 id / 未构建 → **404**（禁止 SPA fallback 把 HTML 当 JS）。  
- `rebuilt(id)` 是 bundle 内容进入图的唯一入口；rev 未变不重组。  
- `onRebuilt` / `onGraphChanged` 拉取模型；监听器异常被兜住。  
- 开发：`dsh-client-hmr` stat 轮询 → `rebuilt` → SSE。生产图不含 HMR 行。

浏览器半 `ctx.modules`：按图 lazy CJS 物化 bundle。

### 6.4 UI 扩展：Conversation Node

Cookbook 路径：

1. Host 定义可回放事件族，稳定业务 id 跨进程；`(kind, id)` 至多一个 start。  
2. Client `ConversationNodeDefinition`：事件 → Context → 确定性 State → keyed renderer。  
3. 重放按 log `seq` 升序；禁止「最新未完成」启发式。窗口内仅有 delta 而无 start 时保持 pending。  
4. 产品渲染不得扫描 Session 窗口或其他已渲染节点。

Chat 插件化因此是 **事件契约驱动的投影**，不是 React 树里的随意插槽堆砌。Tool presentation、workflow run 等同理：client 包 + 域控制器/槽位。

---

## 7. 跨面对齐协议

| 通道 | 方向 | 不变量 |
|---|---|---|
| `SessionEvent` 日志 | Host 追加 → Client 投影 | 模型可见即已记录；UI 不得自造真源 |
| `WebBootGraph` + `/plugins/*` | Host 组合 → Browser 执行 | 图是代码装载 SSOT |
| API gateway / RPC | Client 控制面调用 | GUI 分层笔记；webServer 无业务 |
| HMR SSE | Host → Client | 仅开发 |
| Dynamic Cordis + Inspect | 双面 provider | 会话所有权 + 沙箱 |
| 构建面 | `DSH_BUILD_FACE` host/client | 禁止 Node API 进入 client bundle |

---

## 8. 与替代扩展模型对照

| 维度 | dsh | 典型 SPA feature flag | VS Code Extension | WorkPanel 现状 |
|---|---|---|---|---|
| Host 扩展 | Cordis 服务+事件+可逆 effect | 少 | Extension Host | Rust 模块 + AdapterKind |
| Client 发现 | Host 扫 `dsh.client` 注入 boot 图 | 自管 dynamic import | contributes | 前端写死 / 扩展代理 |
| 真源 | SessionEvent | REST 状态 | 编辑器模型 | SQLite messages/runs + epitaph |
| 组装 | Profile/Bundle 整行 patch | env | package.json | 成员绑定 CLI |
| 动态上限 | Agent define Cordis 包 | 罕见 | 受限 | Extension Host / A2A |
| 卸载 | disposer 强制 | 视作者 | 框架卸载 | 部分（进程级） |

---

## 9. 对 WorkPanel 的专业建议（不嵌入 Cordis）

保持「平台编排、CLI 干活」边界。可移植的是 **契约形态**：

| ID | 建议 | 验收 |
|---|---|---|
| P0-1 | Run 事件日志：`run/start|inject|delta|end`，注入带来源 | Logs 可按 runId 回放 |
| P0-2 | 扩展清单由 Host 组合下发（成员能力、UI 扩展入口），前后端单一 SSOT | 禁止双份 registry |
| P0-3 | epitaph → Context Seam 注入并记账 | 文档与 prompt 可对照 |
| P1-1 | UI 行用稳定 id 投影，禁止「最新未完成」 | 刷新后节点身份不变 |
| P1-2 | 权限/能力关闭必须有 disposer 语义（停路由、停注入） | 关闭后无幽灵监听 |
| P2 | 隔离机验证 `dsh --profile headless` 后再谈 `AdapterKind::Dsh` | 生产 1.8G 机默认关闭 |

**明确不移植：** Cordis Loader、双 tsconfig 面、`__DSH_BOOT__` 原样、动态 Cordis runner。

---

## 10. 风险与证据边界

| 风险 | 说明 |
|---|---|
| 预览破坏性变更 | boot 图字段、`dsh.client`、Loader 插值语义可能变 |
| 双面复杂度 | host/client 两套构建、HMR、rev 一致性运维成本高 |
| 资源 | 全量插件闭包不适合弱主机常驻 |
| 证据 | 本文基于上游文档与 cookbook；未本机验证 HMR/动态插件路径 |
| 类型漂移 | 文中 TypeScript 形状取自文档 `type-equiv` / catalog，以源码生成目录为准 |

---

## 11. 结论

dsh 的插件化是一条控制链：

1. **Composition** 决定树上有哪些包；  
2. **Cordis** 决定 Host 上服务如何依赖、如何用可逆副作用插入策略；  
3. **`clientModules`** 把同一棵树的浏览器半投影为 `WebBootGraph`；  
4. **SessionEvent** 把 Host 事实投影为 Client UI。

因此「Everything is a Plugin」可同时支撑 Web GUI 与 headless：换的是 surface bundle，不是第二套运行时。对编排平台，应复制该控制链的 **SSOT 与可逆性**，而不是复制 Cordis 实现。
