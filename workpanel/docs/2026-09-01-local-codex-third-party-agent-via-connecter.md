# 本机 Codex 通过 WorkPanelConnecter 接入 ohMyWorkPanel Agent 资源

- 日期：2026-09-01
- 研究对象：WorkPanelConnecter `0.2.3`、ohMyWorkPanel `bugfix/v2.1.2`、本机 Codex CLI `0.144.6`
- 源码快照：WorkPanelConnecter `c81a177efa85d8c2d9ea368a1e6d9fe01eaf8025`；ohMyWorkPanel `cfef082d7a9e5d434777374bd6b99ef8cd309cfc`
- 目标：让本设备已经安装并以 ChatGPT 登录的 Codex，作为第三方 Agent 出现在 ohMyWorkPanel 的资源/成员模型中，并由 Connecter 管理身份、在线状态、路由和调度

## 1. 结论

**可行，但不是“写一份 Runner 配置”就完成。**

WorkPanelConnecter 已经覆盖执行侧的大部分基础：Runner 注册、heartbeat/TTL、能力目录、单 Agent 串行与并发上限、任务 lease、ack/renew/result、幂等、设备 enrollment、跨站路由和 Federation。把本机 Codex 包装成只出站的 `CodexRunner`，可以直接复用这些能力。

当前真正缺失的是 **ohMyWorkPanel 入口侧**：

1. ohMyWorkPanel 不读取 Connecter Directory，无法把远端 subject 投影为成员栏中的 Agent；
2. ohMyWorkPanel 的 Agent adapter 只会在它自己的主机 spawn CLI；
3. Connecter 的 Runner dispatch 目前只挂在 pet chat 分支，缺少面向 WorkPanel 服务身份的正式异步 dispatch API；
4. 取消、流式事件和远端 session 仍没有贯通。

因此应把目标拆为两个验收层次：

- **Runner 接入完成**：Codex 出现在 Connecter Directory，在线、可领取任务并回结果；
- **产品接入完成**：Codex 出现在 ohMyWorkPanel 成员栏，用户可 `@`，状态可见，任务、取消、结果和审计全部闭环。

首层可以在 Connecter 内完成；第二层需要同时改 Connecter 与 ohMyWorkPanel。不能把首层冒充最终完成。

## 2. 现状判断

### 2.1 已经可复用的 Connecter 能力

Runner v2 的现有生命周期与本机 Codex 很匹配：

```text
enroll/register -> heartbeat -> poll task -> ack
                -> codex exec -> renew lease -> result
```

关键能力：

- Runner 只向本站 Connecter 出站，不要求在本设备开放公网端口；
- heartbeat TTL 决定 online/offline，离线目标不会静默回落到别的模型；
- 每次 task 领取都有 fencing lease，旧执行者的迟到结果会被拒绝；
- Directory v2 可发布 subject、endpoint、capability、membership、presence；
- Directory v2 routing 与 Federation 可把另一站发起的任务转到本设备所在站；
- production 可要求 enrollment device credential，避免长期静态 runner token。

这部分已经通过本地 Runner、Directory API 和 Federation E2E 门禁。

### 2.2 ohMyWorkPanel 已有 Codex adapter，但不是本目标

ohMyWorkPanel 的内置 Codex adapter 会在 **ohMyWorkPanel 服务器本机**执行 `codex exec --json`。当前实现还会显式选择 DeepSeek-compatible provider 和本机 `:18888` shim。它解决的是“服务器本机运行 Codex-compatible CLI”，不是“调度用户 Windows 设备上现有登录态的 Codex”。

把本机 `auth.json` 复制到服务器不是可接受方案：它扩大凭据暴露面，也破坏“执行与工作区留在设备”的边界。

### 2.3 当前缺口不是 Federation，而是 WorkPanel ingress

Connecter 已能把 pet 发来的 chat 路由到本地或异站 Runner。但 ohMyWorkPanel 自己没有把 `@远端 Agent` 转成 Connecter dispatch 的 provider。即使 CodexRunner 已经注册：

- Connecter ops Directory 可以看到它；
- WorkPet 可通过现有 chat 路径触发它；
- ohMyWorkPanel 成员栏仍不会自动出现它；
- 在 ohMyWorkPanel 手工建一个普通 Agent，只会让服务器尝试 spawn 本地 adapter。

这就是当前最关键的系统边界。

## 3. 推荐目标架构

```text
ohMyWorkPanel（资源与群聊权威）
  Remote Agent Provider
  · 选择/绑定 Directory subject
  · @消息 -> async dispatch
  · 状态、取消、结果 -> 本地 task_run/message
            |
            v
本站 Connecter（WorkPanel Site）
  WorkPanel service identity + /v2/dispatches
  Directory route -> local or federation
            |
     Connecter Host（仅目录汇聚/跨站中继）
            |
            v
本设备所在 Site Connecter
  queue + lease + policy + audit
            ^  只出站
            |
CodexRunner（本设备、当前 Windows 用户）
  heartbeat/poll/ack/renew/result
  spawn: codex exec --json
  workspace allowlist + session map
```

架构职责保持现有命名规则：WorkPanel、用户和 Runner 只连接本站 Connecter；全网唯一 Connecter Host 只负责站点目录与跨站中继，不执行 Codex。

## 4. 本机 CodexRunner 设计

### 4.1 进程与鉴权

新增一个独立 `codex-runner` 进程，建议放在 WorkPanelConnecter 仓库的 `scripts/` 或独立 package 中。它在当前 Windows 用户下运行，从而复用该用户已经存在的 Codex ChatGPT 登录态；不上传、不复制 `~/.codex/auth.json`。

正式环境使用 Connecter enrollment 获得可轮换、可吊销的设备凭证，并向本站 Connecter 注册：

```json
{
  "agentId": "codex-win11-<device-id>",
  "displayName": "Codex · Windows11",
  "agentType": "codex",
  "runtime": "windows-local",
  "protocolVersion": 2,
  "maxConcurrency": 1,
  "labels": { "device": "windows11", "execution": "local" },
  "capabilities": [
    { "name": "code.execute", "version": "1" },
    { "name": "repo.edit", "version": "1" }
  ],
  "groups": [
    {
      "groupRef": "<authority>/<group>",
      "env": "prod",
      "groupId": "<ohMyWorkPanel group id>",
      "agentName": "Codex · Windows11"
    }
  ]
}
```

Runner 自报 capability 只能作为声明；是否允许 `repo.edit` 必须由 enrollment scope 和 Connecter policy 授权。

### 4.2 Codex 调用方式

首版应使用稳定、简单、可审计的非交互 CLI：

```text
codex exec --json -C <allowlisted-workspace> \
  --sandbox workspace-write --ask-for-approval never <prompt>
```

Windows 实现应直接构造 argv，不拼 shell 字符串。不要使用 `--dangerously-bypass-approvals-and-sandbox`。`-C` 必须来自本机管理员配置的 binding -> workspace 映射，不能由远端 prompt 提供。

JSONL 至少处理：

- `thread.started.thread_id`：可选的 session 映射；
- `item.completed` 且 `item.type=agent_message`：最终文本；
- `turn.failed` / `error`：失败原因；
- 进程退出码、stderr、超时和输出大小上限。

本机版本的 `app-server`、`exec-server` 和 remote-control 仍标记 experimental。它们适合后续需要更细交互时评估，不应成为首版依赖。

### 4.3 heartbeat 与 lease

heartbeat 必须由独立定时器发送，不能只放在“任务执行完后”的主循环里。Codex 任务可能超过 60 秒；执行期间还需要按 lease 的一半周期 renew。

如果 renew 返回 stale lease、任务被取消或进程超时，Runner 应终止本地 Codex 子进程，并报告一致的终态。默认 `maxConcurrency=1`，先与 ohMyWorkPanel 的同 Agent 串行语义对齐。

### 4.4 session 策略

建议分两步：

1. POC 使用 `--ephemeral` 或每任务新会话，先证明身份、路由、执行和结果；
2. 产品版在本设备保存 `groupRef + subjectId + workspace -> threadId` 映射，后续用 `codex exec resume`。

session 只应存在本机。映射需要原子落盘、损坏恢复和工作区变化失效规则；resume 失败可清除映射并重试一次新会话。不要用全局 `--last`，否则不同群会串会话。

## 5. Connecter 需要补的正式入口

### 5.1 不建议把 pet token 当服务凭证

现有 `/v1/chat` 的 Runner 路由位于 pet chat 分支，适合 WorkPet 和 POC。正式的 ohMyWorkPanel provider 不应伪装成 pet，也不应拿 ops token 做日常任务投递。

建议增加 WorkPanel service identity，并提供：

```text
POST /v2/dispatches
GET  /v2/dispatches/{id}
POST /v2/dispatches/{id}/cancel
GET  /v2/directory/subjects|endpoints   （受 group/policy scope 约束）
```

`POST /v2/dispatches` 最少包含：

```json
{
  "idempotencyKey": "<workpanel task_run id>",
  "groupRef": "<stable group ref>",
  "targetSubjectId": "<stable directory subject>",
  "prompt": "...",
  "context": {
    "source": "ohmyworkpanel",
    "messageId": "...",
    "runId": "..."
  },
  "requiredCapabilities": ["code.execute"]
}
```

返回 `202`、dispatch id、trace id、路由目标和初始状态。实现内部复用现有 `resolveRoute`、queue、lease 和 federation，不再造第二套任务系统。

### 5.2 结果与流式

POC 可以轮询现有 run，产品契约应把数据库内部的 `detail_json` 包装为稳定 DTO。首版只需 running + terminal；后续可用 SSE/WebSocket 投递标准化事件。

Runner 直接 `postAsAgent` 回写 WorkPanel 与 WorkPanel provider 自己写消息只能选一个，否则会产生双回复。推荐由 provider 负责写本地 `task_run` 和 Agent 消息；Runner result 对该来源设置 `writeBack=false`。

## 6. ohMyWorkPanel 需要补的 Remote Agent Provider

### 6.1 资源投影

管理员从受 scope 限制的 Directory 中选择 subject，再明确绑定到某个群；不要把全网所有 endpoint 自动写进所有群。

建议在 `agent_profiles` 或独立表保存：

- `provider=connecter`；
- `remote_subject_id`；
- `group_ref`；
- `required_capabilities`；
- `site_id`、display name 的缓存；
- last presence / last sync / policy state。

稳定身份必须用 Directory subject id，display name 只用于显示。改名不应创建新 Agent。

### 6.2 调度

ohMyWorkPanel 的 `schedule_group` 遇到 `provider=connecter` 时：

1. 创建本地 task run；
2. 用 task run id 作为 idempotency key 调 `POST /v2/dispatches`；
3. 保存 remote dispatch id / trace id；
4. 更新 queued/running 状态；
5. 收到终态后写 Agent 消息并完成本地 run；
6. 用户取消时调用远端 cancel，并等待确认。

这个 provider 不应走本机 CLI manifest。Manifest 的职责是 spawn ohMyWorkPanel 主机上的 CLI；远端 subject 是网络资源、在线状态和租约模型，生命周期不同。

### 6.3 UI

成员栏至少显示：

- `远端 · <site>` 标记；
- online / stale / offline / policy denied；
- queued / running；
- capability 摘要；
- 最后心跳时间和 route explain 的简化原因。

Runner TTL 过期时，发送应明确失败或排队策略化处理，不能静默切换到服务器本地 Codex 或其它模型。

## 7. 可快速验证的 POC

在不改 ohMyWorkPanel 前，可以先做 **执行侧 POC**：

1. 在本站 Connecter 预配或 enroll `codex-win11-*`；
2. 实现最小 CodexRunner；
3. 通过现有 WorkPet `/v1/chat` 发任务；
4. 验证 register、online、ack、renew、真实 `codex exec`、result；
5. 若跨站，再验证 Host directory advertise 和 federation result 回传。

这个 POC 证明“Connecter 能调本机 Codex”，但不证明“Codex 已成为 ohMyWorkPanel Agent 资源”。后者必须等 Remote Agent Provider 过线。

不推荐用 custom chatbot 兼容层偷渡：ohMyWorkPanel 的 chatbot 路径是 30 秒同步 completion，没有工作区、lease、取消和 coding-agent 生命周期。

## 8. 实施顺序

### P0：CodexRunner 执行侧

- 新增 `codex-runner`，实现 register/heartbeat/poll/ack/renew/result；
- 固定 workspace allowlist、maxConcurrency=1、进程超时和输出上限；
- JSONL parser 使用 fixture 单测，并用可替换 spawn 做协议门禁；
- 手工授权后跑一次真实 Codex canary，记录额度、输出和本地文件影响。

### P1：WorkPanel service dispatch API

- 新建 service identity/scope，不复用 pet/ops；
- `/v2/dispatches` 复用现有 route/queue/federation；
- 稳定 run DTO、幂等和取消；
- audit/trace 覆盖来源 WorkPanel run id 到 Runner result。

### P2：ohMyWorkPanel Remote Agent Provider

- Directory 选择与显式群绑定；
- proxy member / remote subject 持久化；
- `@` 调度、状态、结果和取消闭环；
- 避免 provider 写回与 Connecter `postAsAgent` 双写。

### P3：跨站与稳态

- 真实两 Site + 独立 Connecter Host；
- Runner 离线、站点重启、Host 暂时不可用、迟到结果、重复 result；
- session resume、滚动升级、凭证轮换和吊销；
- 流式事件、指标和告警。

## 9. 验收标准

只有以下条件都满足，才能称为“本机 Codex 已接入 ohMyWorkPanel Agent 资源”：

1. Directory endpoint 显示正确 stable subject、capability、site、online；
2. ohMyWorkPanel 成员栏出现同一 remote subject，并显示在线状态；
3. 群里 `@Codex · Windows11` 后，本设备真实启动 Codex CLI；
4. task run 的 queued/running/completed 或 failed 与 Connecter task 一致；
5. 最终回复只出现一次，并能追溯 WorkPanel run id、Connecter trace id、Runner task id；
6. 停掉 Runner 超过 TTL 后显示 offline，调度不静默落到别的执行端；
7. 取消会终止本设备子进程，旧 lease 的迟到结果不会覆盖终态；
8. 同一 idempotency key 重试不产生第二次 Codex 执行；
9. 设备凭证可轮换、可吊销，Codex 登录态没有离开本设备；
10. 跨站目标经过真实 Site Connecter -> Host -> Site Connecter 闭环验证。

## 10. 风险与建议

| 风险 | 建议 |
| --- | --- |
| 把 Runner 注册误当产品接入完成 | 分别设 Runner gate 与 WorkPanel UI E2E gate |
| 复制 Codex 登录态到服务器 | Runner 在本设备当前用户下执行，只持有 Connecter device credential |
| prompt 选择任意工作区 | binding 到本机 allowlist；远端不可传绝对路径覆盖 |
| unattended agent 权限过大 | workspace-write + approval never；禁止 bypass sandbox；能力需 policy 授权 |
| 长任务 heartbeat/lease 过期 | heartbeat 独立定时；执行中按 lease/2 renew |
| 结果双写 | WorkPanel provider 路径固定 `writeBack=false`，由 provider 写消息 |
| session 串群 | 按 groupRef + subject + workspace 映射 thread id，禁止 `--last` |
| CLI JSONL 升级漂移 | 版本探测、fixture contract、未知事件容忍、canary |
| pet/ops token 权限混用 | 增加 WorkPanel service identity 与最小 scope |

## 11. 证据来源与边界

### 本地源码

- WorkPanelConnecter：`D:\AI\workpanelConnecter`，commit `c81a177efa85d8c2d9ea368a1e6d9fe01eaf8025`
  - `docs/protocol/runners.md`
  - `docs/protocol/directory-v2.md`
  - `src/relay/runners.js`
  - `src/relay/services/dispatchService.js`
  - `src/relay/handlers.js`
  - `src/workpanelClient.js`
- ohMyWorkPanel：`D:\AI\LinlisWorkPanel`，commit `cfef082d7a9e5d434777374bd6b99ef8cd309cfc`
  - `src-tauri/src/adapters/codex.rs`
  - `src-tauri/src/adapters/mod.rs`
  - `src-tauri/src/adapters/manifest.rs`
  - `src-tauri/src/adapters/chatbot.rs`
  - `src-tauri/src/scheduler.rs`
  - `src-tauri/src/web.rs`

### 本机命令

- `codex-cli 0.144.6` 的 `--help`、`exec --help`、`exec resume --help`、`app-server --help`、`login status` 和脱敏 `doctor`；
- `npm run test:runner`、`npm run test:directory-api`、`npm run test:federation-e2e` 均通过。

### 外部资料

- [OpenAI Codex CLI reference](https://developers.openai.com/codex/cli/reference/)
- [OpenAI Codex app server](https://developers.openai.com/codex/app-server/)

本次网络无法抓取上述 OpenAI Docs 页面，能力判断以本机已安装版本的实际命令帮助为准。未运行真实 Codex 模型调用，未实现 Runner，未部署真实双 Site，也未验证 ohMyWorkPanel UI 闭环；因此结论是“架构可行、基础协议已具备、产品入口待实现”，不是“已经接入完成”。
