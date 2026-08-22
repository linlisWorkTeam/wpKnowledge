# WorkPanelConnecter 当前实现分析

| 项 | 内容 |
|---|---|
| 日期 | 2026-08-22 |
| 研究对象 | `linlisWorkTeam/workpanelConnecter` |
| 源码基线 | `main@3cf0d68c9242a7fce322363940413345bbbac34f` |
| 版本 | `0.2.3` |
| 研究范围 | Site Connecter/Relay、Connecter Host、Runner、Directory v2、跨站 Federation、WorkPet 客户端 |
| 验证 | `npm run test:release-local` 通过全部 51 个本地门禁 |

## 一句话结论

WorkPanelConnecter 已实现为“每站一个 Site Connecter + 全网一个 Connecter Host”的中间件：Site Connecter 负责本站 WorkPet/User、WorkPanel 和 Runner 的鉴权、代理、可靠投递与调度；Connecter Host 只负责 Site peer 注册、全局目录交换和跨站 durable federation，不承接本站聊天，也不执行 Agent。当前实现已经超出早期 relay/MVP，形成了可运行的本地三进程跨站闭环，但真实多服务器部署、生产密钥运维和长时 soak 仍不在本地证据范围内。

## 1. 系统边界与拓扑

权威架构由 `README.md`、`docs/architecture.md` 和 `docs/CONNECTER-EVOLUTION.md` 定义：

```text
本站：WorkPet/User ──► Site Connecter ──► WorkPanel / Runner

跨站：WorkPet A ─► Connecter A ─► Connecter Host ─► Connecter B ─► Runner/WorkPanel B
结果：Runner B ─► Connecter B ─► Connecter Host ─► Connecter A ─► WorkPet/WorkPanel A
```

角色权威边界如下：

- WorkPet 只负责用户交互、桌面外观和 Connecter 配置，不直连 WorkPanel 或 Host。
- Site Connecter 保存本站身份映射、消息/任务状态、Runner lease、目录投影和联邦 inbox/outbox；它不执行 Agent。
- WorkPanel 仍是群、成员、会话正文和业务 Agent 身份的事实源。
- Runner 是出站适配器，实际执行任务；它不决定群消息权威，也不接受 Connecter 的入站连接。
- Connecter Host 只开放 peer/federation/control 路径，不暴露 WorkPet、WorkPanel 或 Runner 执行接口。

因此，Host 是跨站控制面与数据面中继，不是所有站内消息的强制代理。站内路径在 Host 故障时仍可以独立工作。

## 2. 进程启动与初始化

入口是 `bin/connecter-relay.js` → `src/relay/server.js`：

1. `loadRelayConfig()` 读取 `CONNECTER_RELAY_CONFIG` 或 `config/relay.json`。
2. `openDb()` 打开 SQLite，设置 WAL/foreign keys，并通过 `src/relay/migrations.js` 校验迁移 checksum、备份旧库并应用迁移。
3. `syncConfigPets()` 将 `pets[]`、默认群绑定和 session token hash 写入数据库。
4. `syncConfigRunners()` 将静态 Runner 预配和 binding 投影为 Runner、endpoint、capability、membership、presence。
5. 启动时回收过期任务并执行 `resumePending()`，重投仍为 `accepted` 的上行消息。
6. `createRelayServer()` 建立原生 Node HTTP server；监听后 `startHostJoin()` 为 Site Connecter 启动 Host 注册/心跳/目录同步/联邦收发循环。

`host.role` 决定进程边界：`host` 只接受 `/v1/host/*`、`/v1/federation/*` 和 `/v1/ops/*`；`connecter` 通过 Host URL 主动出站加入；未配置时为 standalone。

## 3. 认证与 HTTP 面

HTTP 路由集中在 `src/relay/server.js`，业务编排主要在 `src/relay/handlers.js`。请求先进入 `authenticateRequest()`：

- pet：SQLite `sessions` 中的 token hash，附带 pet 级 chat/console 限流和 session 状态。
- ops：`config.auth.tokens[]`，用于运维和旧版直路由。
- runner：`runners.token_hash`，可选要求已审批 device credential。
- peer：`connecter_peers.token_hash`，仅允许 Host peer 联邦接口。

主要 API 面：

| 面 | 典型接口 | 作用 |
|---|---|---|
| 健康/配置 | `GET /v1/health`、`GET /v1/envs` | 站点状态、WorkPanel 槽位和 Host link 状态 |
| WorkPet 群控制台 | `POST /v1/auth/login`、`GET /v1/groups*` | 用 WP 用户登录并仅暴露该用户可见的群/成员/历史 |
| 消息 | `POST /v1/chat`、`GET /v1/messages`、`GET /v1/runs/:id` | 上行受理、下行 cursor 轮询、运行状态 |
| Runner | `/v1/agents/register|heartbeat|tasks|tasks/ack|tasks/renew|tasks/result` | 出站注册、心跳、lease 领取、结果回写 |
| Directory/enrollment | `/v2/enrollments`、`/v2/directory/*`、`/v2/credentials/*` | 稳定主体、endpoint、能力、审批凭证和路由解释 |
| Federation | `/v1/federation/messages|pull|ack|result|directory/*` | Host 中继、目录广告和目标站处理 |
| Ops | `/v1/ops/*` | task、policy、peer、security delivery、trace、health detail |

## 4. 站内消息闭环

### 4.1 WorkPet 到 WorkPanel

`POST /v1/chat` 的 pet 路径在 `handlers.js` 中完成：

1. 解析 `env`、group id/name，并通过 WorkPanel `/api/groups`、`/api/presence` 确认群和成员。
2. `selfInGroup()` 优先按登录 WP `userId` 匹配 `authUserId`；canary 尚未绑定用户时才回退为信任 WP 列表。
3. `resolveChatTarget()` 按群成员最长匹配 `@Agent`；没有 `@` 时只选择群 `adminMemberId` 对应的活跃 Agent。
4. `ensureAgentInstance()` 创建/复用 `(pet, env, group, agent)` 实例。
5. `acceptMessage()` 调用 `acceptUpMessage()`，在 SQLite 事务中写入 `messages`，以 `id` 唯一约束提供全局幂等。
6. 若目标绑定本地 Runner，则转入 Runner task queue；否则进入 `deliverWithRetry()`，通过 `workpanelClient.js` 登录 WorkPanel 并 POST `/api/messages`。
7. 成功后 `markDelivered()` 将上行消息置为 `delivered`，建立 `runs`，并插入一个 down `delivery.ack`，供 `GET /v1/messages?since=` 读取。

WorkPanel 保存群聊正文；Connecter 只保存投递 envelope、状态和必要运行信息。群控制台的 `GET /v1/groups/:id/messages` 是实时代理，不把完整 transcript 镜像进 SQLite。

### 4.2 WorkPet 客户端

`apps/workpet/ui/connecterApi.js` 是无依赖 JS SDK。Tauri UI 从 `~/.workpet/config.json` 读取 `connecterBaseUrl`、token、env、group；`src-tauri/src/main.rs` 的 `get_config/set_config` 负责本地配置读写。

客户端先调用 `/v1/auth/login` 取得 pet token，之后通过 SDK 调用 `/v1/groups`、`/v1/groups/:id`、`/v1/groups/:id/messages` 和 `/v1/chat`。展开面板约每 2 秒拉取 WorkPanel transcript，收起态/运行状态则按 cursor 轮询 `/v1/messages` 和 `/v1/runs/:id`。桌面窗体由 Tauri 透明、无边框、置顶窗口承载，Live2D/状态皮肤与 Connecter 数据面解耦。

## 5. Runner 调度与可靠性

Runner 采用只出站 pull 的 NAT-friendly 模式，核心实现为 `src/relay/runners.js`、`services/dispatchService.js` 和 `services/taskQueueService.js`：

- 静态 `config.runners[]` 启动时预配，或通过 `/v1/agents/register` 动态注册；绑定按 `(env, group, agentName, role)` 唯一。
- heartbeat 更新 `last_seen_at`，默认 60 秒 TTL；过期时新消息直接返回 `503 runner_offline`，不会静默降级到 WorkPanel。
- poll 在 SQLite 写事务中原子领取 queued task，创建一次性 `leaseToken`，只保存 hash，带 `lease_until`、attempt 和并发限制。
- Runner 必须用当前 lease token `ack`、`renew`、`result`；过期或旧执行者返回 `409 STALE_LEASE`。
- `(taskId, resultId)` 是结果幂等键；同 payload 重放返回 `duplicate`，同 resultId 不同 payload 返回冲突。
- 任务 lease 超时后重新入队，超过 max attempts 进入 dead；ops 可手工 requeue/cancel。
- 终态结果先写入 Connecter 的 down message/run，再 best-effort 以目标 Agent 成员身份回写 WorkPanel 群线程；回写失败不阻塞结果提交。

这使 Connecter 管理在线状态和调度，但执行环境仍由 Runner 决定；DeepSeek Harness 只是可能的 Runner 实现，不是核心耦合。

## 6. Directory v2 与路由

`src/relay/services/identityService.js` 产生：

- `stableSubjectId = UUID(sha256(siteId/kind/localId))`，区分 user、agent、workpet、service；
- `groupRef = wp:<authority>:<urlencoded groupId>`；
- `traceId/correlationId/causationId`，贯穿跨站请求。

`directory.js` 将 WorkPanel 成员和 Runner 注册投影到 `subjects`、`memberships`、`endpoints`、`capabilities`、`presence_observations`。远端路由以 federation route 的 endpoint 形式导入，TTL 过期后不可选。

`routeResolver.js` 先检查群成员资格、endpoint active/未过期和 required capabilities，再按本地优先、priority、load、endpoint id 排序；同显示名对应多个稳定主体时返回 `AMBIGUOUS_SUBJECT`。`directoryV2Shadow` 只记录新路由，`directoryV2RoutingEnabled` 才实际切换；没有能力匹配的路由返回 `503`。

## 7. Enrollment、安全与策略

接入流程是 enrollment code → ops approve/reject → device credential → rotate/revoke。凭证只存 hash，scope 包含 sites/groups/capabilities/operations；启用 `requireDeviceCredentials` 后静态 Runner token 不能继续作为生产接入凭证。

联邦 envelope 使用 HMAC 签名，支持 active/next/revoked key；生产配置可要求外部 secret file/env、HTTPS 和 mTLS。`federationClient.js` 使用 `https.request`，证书校验固定为 `rejectUnauthorized: true`。`accessPolicy.js` 默认拒绝，按 origin site、target site、groupRef、subject、operation、direction、capability 和 data classification 匹配；显式 deny 优先于 allow。安全 delivery、policy、enrollment、peer rotation/revoke 和 trace 都有 audit/telemetry 投影。

## 8. 跨站 Federation 闭环

### 8.1 Site Connecter 出站

`hostJoin.js` 周期性调用 Host 的 peer register/heartbeat。联邦启用后每轮还会：

1. 通过 `federationSite.js` 广告本站有效 Runner route，并导入 Host 返回的远端 route；
2. flush 本站 `federation_outbox`；
3. pull Host 为本站租出的 inbox；
4. ack、处理 inbox、向 Host 提交最终 `delivered/failed` result。

`dispatchToRunnerIfBound()` 在 Directory v2 路由命中本地 endpoint 时沿用本地 task queue；命中远端 Site 时创建 `chat.command` envelope 写入 outbox，并立即尝试 flush。远端 Runner 完成后生成独立的 `run.event`，沿反向路径返回源站。

### 8.2 Host 中继

`federationHost.js` 的 `acceptFederationMessage()` 依次执行：envelope schema/TTL/hop/payload 校验、originSite 与 peer 身份匹配、签名验证、目标 Site 预配、ACL、quota 和幂等检查，然后事务写入 `federation_messages` 与 `federation_deliveries`。

目标 Site 通过 `pull` 获取一次性 federation lease；Host 保存 lease hash 和超时，重复 pull 或 Site 崩溃会回收并重新排队。Site ack 后进入 acknowledged，处理完成再调用 result；Host 以 `(originSite, messageId)` 幂等，重复 envelope 同体返回已有状态，内容冲突返回 `409`。Host 不执行目标任务，只维护跨站传输状态。

### 8.3 目标 Site 处理

目标 Site 把 Host 返回的 envelope 落到 `federation_inbox`，先 ack，再通过 processing lease 消费：

- `chat.command` 解析 canonical GroupRef，按本地 Directory 找到 Runner，创建带 federation 元数据的本地 task；
- `run.event` 用 `correlationId` 做 first-terminal-wins，将源站 up message/run 和 down message 投影为终态，并 best-effort 回写源 WorkPanel；
- 处理失败进入 retry，超过 inbox max attempts 进入 dead，之后向 Host 报告 failed。

因此，跨站“受理”与“执行完成”是两个 durable 阶段；Host 受理成功不等价于 Runner 已完成。

## 9. 持久化模型

SQLite 使用 WAL 和单进程 `writeTx()` 写事务串行化。主要表按责任域分为：

- 身份：`users`、`pets`、`sessions`、`agent_instances`；
- 站内消息：`messages`、`runs`、`delivery_log`；
- Runner：`runners`、`runner_bindings`、`runner_tasks`、`runner_task_results`、`runner_task_audit`；
- Directory：`subjects`、`endpoints`、`capabilities`、`memberships`、`presence_observations`、`route_decisions`；
- 接入/安全：`enrollment_requests`、`device_credentials`、`federation_policies`；
- Federation：`federation_messages`、`federation_deliveries`、`federation_receipts`、Site `federation_outbox/inbox`、`federation_routes`、`federation_run_terminals`；
- 运维：`audit_events`、`audit_events_archive`、`telemetry_events`。

迁移 001–012 在启动时校验 checksum；新库从 `schema.sql` 建立完整快照，旧库升级前可 `VACUUM INTO` 备份。该方案适合一站一进程的当前部署边界；它不是多 Connecter 共享同一 SQLite 的 HA 方案。

## 10. 证据与验证

本轮读取的源码/文档证据均来自 `D:\AI\workpanelConnecter` 的 `main@3cf0d68c9242a7fce322363940413345bbbac34f`，重点包括：

- `src/relay/server.js`、`handlers.js`：HTTP 路由与权限边界；
- `src/relay/db.js`、`schema.sql`、`migrations.js`：SQLite/WAL、事务和迁移；
- `src/relay/messaging.js`、`delivery.js`、`services/messageService.js`：消息幂等、投递重试和 ack；
- `src/relay/runners.js`、`services/dispatchService.js`、`services/taskQueueService.js`：Runner 注册、路由、lease/fencing、恢复；
- `src/relay/directory.js`、`routeResolver.js`、`enrollment.js`、`credentialStore.js`：身份、目录、能力、接入和凭证；
- `src/relay/hostJoin.js`、`hostPeers.js`、`federationHost.js`、`federationSite.js`、`federationClient.js`：Host peer、跨站中继、inbox/outbox 和 TLS；
- `src/workpanelClient.js`、`apps/workpet/ui/connecterApi.js`、`apps/workpet/ui/main.js`、`apps/workpet/src-tauri/src/main.rs`：WorkPanel 适配和桌面端连接；
- `docs/architecture.md`、`docs/api-relay.md`、`docs/protocol/*.md`、`docs/runbooks/federation-local-lab.md`：权威契约与证据边界。

执行：

```text
npm run test:release-local
RELEASE_LOCAL_GATE_OK gates=51
```

该门禁实际覆盖 smoke、Relay、Runner、Directory、enrollment、Federation 正常/故障恢复、WorkPanel outage、策略、安全、mTLS、trace、备份恢复和 7 秒短 soak。

## 11. 结论、建议与边界

### 结论

1. 当前项目的核心已经是“站点可靠投递与调度中间件”，而非简单 HTTP proxy。
2. WorkPanel 保持业务事实源，Runner 保持执行权，Host 保持跨站传输与目录汇聚，职责拆分是正确的。
3. 本地可靠性链条已完整覆盖：消息幂等、重试、Runner heartbeat、lease/fencing、跨站 inbox/outbox、ACL、签名、mTLS 和审计。
4. `npm run test:release-local` 的 51 项通过可以证明代码在临时本地拓扑中的行为，但不能单独证明生产网络和运维条件。

### 建议

1. 继续保持 Host 不承接站内流量；下一步优先做真实双 Site + 独立 Host 的网络验收。
2. 把多服务器 mTLS、外部 signing key/secret store、peer token rotation 和 firewall/NAT 写成部署级 runbook，并保留实测证据。
3. 将跨站 outbox/inbox/Host delivery 的指标接入外部告警，至少覆盖 backlog、lease expiry、dead letters、policy deny、write-back failure。
4. 在 Directory v2 正式启用前持续运行 shadow 对比，避免显示名路由与稳定 Subject 路由出现漂移。
5. 统一协议文档中的方法声明：当前源码和测试使用 `GET /v2/routes/explain`，而 `docs/protocol/directory-v2.md` 的表格仍写成 `POST`，应修正文档或兼容代码。
6. 只有在单 Host 成为实际 SLA/容量瓶颈后，才引入 Host HA、外置数据库或 Raft/etcd；不要复制 WorkPanel 正文。

### 证据边界

- 已验证的是当前源码、临时 SQLite/进程和本地测试中的行为；测试输出不能替代真实生产部署。
- `test:mtls-handshake` 使用临时 CA/证书，不能替代真实双 Site、DNS、反向代理、证书轮换和防火墙验证。
- `test:soak-smoke` 只有 7 秒；真实 72 小时 soak、外部告警和 Windows Authenticode 签名仍是环境门禁。
- 本报告没有修改 `workpanelConnecter` 业务代码；本轮只更新知识库报告。
