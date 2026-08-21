# WorkPanel Connecter 愿景符合度与可扩展性评审

| 项 | 内容 |
|---|---|
| 日期 | 2026-08-21 |
| 研究对象 | `linlisWorkTeam/workpanelConnecter` |
| 源码基线 | `main@e5b51eb9f89f9bcbb19480d58dc2de230d7e7591` |
| 用户愿景 | 每站 Connecter 连接异地 Agent 与 User；中心化 Connecter Host 会合所有 Connecter；消息经 Connecter 中介 |
| 验证 | `test:host-peers`、`test:runner-handler`、`test:runner`、`test:relay-unit` 全部通过 |

## 一句话结论

当前代码已经形成“WorkPet/User → 站点 Connecter → 本站 WorkPanel/异地 Runner”的可运行站点内数据面，也实现了“站点 Connecter → 中心 Connecter Host”的注册和心跳控制面；但 **Connecter Host 还不是消息中继器**，没有跨站寻址、消息转发、持久队列、回执和故障恢复。因此，组件命名与目标拓扑大体正确，完整愿景只实现到 E2，跨站数据面 E3 尚未落地。

## 愿景符合度矩阵

| 愿景 | 当前代码 | 判断 |
|---|---|---|
| Connecter 是 WorkPanel 中间件 | WorkPet 只调用 Connecter；Connecter 代理群、消息、presence，并向 WorkPanel 投递 | **符合** |
| PanelPet/WorkPet 与 Connecter 是前后台 | UI 位于 `apps/workpet`，后端接口位于 `src/relay` | **符合，但产品正式名是 WorkPet，不是 PanelPet** |
| 每站点部署一台 Connecter | `host.role=connecter`、`siteId`、本站 backend/runner 配置已表达站点边界 | **符合设计** |
| 不同服务器的 Agent 接入 | Runner 支持 register、heartbeat、TTL、poll、result，NAT 友好 | **站点范围已实现** |
| 不同服务器的 User 接入 | User 通过各自 WorkPet 登录本站 WorkPanel；群成员与 presence 由 WP 提供 | **站点范围已实现，跨站身份未统一** |
| 所有 Connecter 注册到中心 Host | `hostJoin.js` 定时 register + heartbeat；Host 持久化 `connecter_peers` | **已实现控制面骨架** |
| Host 是中心消息中继器 | Host API 只有 peer register/heartbeat/list；源码中没有 federation/forward/inbox/outbox 路由 | **未实现** |
| 所有消息经 Connecter 中介 | WorkPet/Runner 路径经本站 Connecter；本站聊天明确绕过 Host | **若指本站 Connecter则符合；若指所有消息都经 Host则不符合** |

## 当前真实架构

```text
WorkPet / User
      │ REST + pet token
      ▼
站点 Connecter ───────────────► 本站 WorkPanel（群聊权威、User/群/消息）
      │
      ├── SQLite：messages / runs / delivery_log
      ├── Runner registry + heartbeat TTL + task queue
      └── register + heartbeat ──► Connecter Host
                                      └── 目前仅 peer registry

远端 Agent Runner ── register/heartbeat/poll/result ──► 站点 Connecter
```

关键边界是合理的：WorkPet 不直连 WorkPanel/Host；Runner 不在 Connecter 内执行；WorkPanel 保持群聊事实源；Host 不执行 Agent。问题不在角色划分，而在 Host 数据面尚为空。

## 已有架构的可扩展性

### 值得保留

1. **执行与中继解耦**：任意执行器只要实现 `/v1/agents/*` 即可接入，方向优于在 Connecter 内硬编码具体 Agent。
2. **NAT 友好的 pull 模式**：Runner 主动出站注册、心跳和取任务，适合家庭、办公室和不同云服务器。
3. **群聊事实源唯一**：WorkPanel 保存群与正文，Connecter 只保存投递信封和运行状态，避免双主数据。
4. **基础可靠性已有地基**：SQLite WAL、消息 id 幂等、失败重试、游标轮询、Runner TTL 和同 Runner 串行。
5. **角色已经分离成模块**：`runners.js`、`hostJoin.js`、`hostPeers.js`、`wpSlots.js` 已从 HTTP server 分出，便于继续抽象。

### 主要扩展瓶颈

1. **Host 只有成员表，没有消息协议**：没有站点/群/Agent 的全局路由目录，也没有跨站 envelope、hop、TTL、ack、outbox/inbox 或死信。
2. **Runner 队列缺 lease**：poll 后任务直接变成 `dispatched`；没有 `lease_until`、attempt、ack 或超时重投。Runner 崩溃会留下永久 in-flight，后续任务也因“一条 dispatched”而无法领取。
3. **注册仍需静态预配**：Runner 与 Host peer 都必须先出现在 `relay.json`；适合早期安全白名单，不适合大规模自助接入、审批和 token 生命周期管理。
4. **路由键仍是本地坐标**：核心键是 `env/group_id/agent_name`，缺 `site_id`、全局主体 ID、tenant/namespace；跨站后容易碰撞。
5. **能力模型缺失**：Runner 没有正式 capabilities、负载、并发、版本、模型、资源标签，当前只能按精确绑定路由，不能做能力调度。
6. **SQLite 与进程内写串行限制横向扩展**：`writeTx` 用进程内 Promise 链串行化；适合单站单实例，不支持多进程共同消费，也没有 fencing。
7. **数据库无版本迁移体系**：启动时直接执行 `CREATE TABLE IF NOT EXISTS`；跨站协议演进后难以安全升级、回滚和校验版本。
8. **应用层过于集中**：`handlers.js` 约 700 行，同时编排认证、群、消息、Runner、Host；联邦加入后会迅速成为耦合中心。
9. **认证与密钥仍是 MVP 级别**：静态 bearer、配置文件明文 token、无 key id/轮换/短期凭证/mTLS/站点级 ACL。
10. **观测与审计不足**：缺统一 trace/correlation ID、跨 hop 投递时间线、指标与结构化审计，跨站故障将难定位。

## 对中心化愿景的一个必要澄清

“所有消息通过 Connecter 中介”与“所有消息通过 Connecter Host”是两种不同约束。当前已拍板设计选择：

- 本站消息：`WorkPet → 本站 Connecter → 本站 WorkPanel/Runner`，Host 故障时仍可用；
- 跨站消息：`Connecter A → Host → Connecter B`；
- Host 是中心化会合与跨站中继，不是所有本站流量的强制代理。

建议保留这一选择。让全部本站消息也绕行 Host 会扩大故障域、延迟和带宽成本，却没有明显业务收益。中心化应该体现在 **全局目录、策略、跨站路由和审计**，不必体现在每一条本地数据包。

## 推荐目标架构

```text
                         Connecter Host
                 ┌─────────────────────────┐
                 │ Global Directory        │
                 │ Policy / Route Resolver │
                 │ Federation Inbox/Outbox │
                 │ Delivery State / Audit  │
                 └───────────┬─────────────┘
                             │ mTLS / signed envelope
               ┌─────────────┴─────────────┐
               ▼                           ▼
       Site Connecter A             Site Connecter B
   ┌────────────────────┐       ┌────────────────────┐
   │ Local Directory    │       │ Local Directory    │
   │ Durable Task Lease │       │ Durable Task Lease │
   │ WP Adapter         │       │ WP Adapter         │
   │ Runner Adapters    │       │ Runner Adapters    │
   └──────┬──────┬──────┘       └──────┬──────┬──────┘
          │      │                     │      │
       WorkPet  Runner              WorkPet  Runner
          │                            │
       WorkPanel A                  WorkPanel B
```

Host 保存“可路由的全局投影”和跨站投递状态，不复制 WorkPanel 的完整群聊正文。正文事实源仍是目标 WorkPanel；Connecter/Host 保存必要 envelope、幂等键、审计和投递结果。

## 演进路线

### P0：先修站点内可靠性与边界

1. 给 `runner_tasks` 增加 `lease_owner`、`lease_until`、`attempt`、`available_at`、`last_error`；poll 变成原子 claim，超时自动回队。
2. 增加 task ack，终态 result 使用幂等键和 fencing token，防止旧执行者覆盖新执行结果。
3. 引入版本化 migration，并为从旧 SQLite 升级添加门禁测试。
4. 把 `handlers.js` 拆为 application services：identity、directory、messaging、dispatch、federation、audit；HTTP 只做传输适配。
5. 固化全局 ID：`siteId + subjectId`，群/Agent/User 使用稳定 UUID，不以显示名作身份。

### P1：补全 Agent/User 目录和调度模型

1. Runner 注册增加 capabilities、version、maxConcurrency、labels、load、supportedProtocol。
2. 将“预配白名单”演进为 enroll → approve → issue short-lived credential → rotate/revoke。
3. 建立 `subjects`、`memberships`、`endpoints`、`presence` 投影，区分 User、WorkPet、Agent Runner、WP Agent member。
4. 路由器按群成员资格、能力、健康、负载、数据驻留和优先级决策；默认同 Agent 串行，但支持显式并发上限。

### P2：实现 Connecter Host 联邦数据面（E3）

1. 先冻结 federation envelope：`messageId`、`correlationId`、`originSite`、`targetSite`、`groupId`、`subject`、`payloadRef/content`、`createdAt`、`expiresAt`、`hop`、`signature`。
2. Site Connecter 使用出站长轮询/WebSocket/gRPC stream 连接 Host；避免 Host 主动穿透站点 NAT。
3. Host 和 Site 两端都使用 durable outbox/inbox；状态至少包含 accepted、forwarded、delivered、failed、expired。
4. 以 `(originSite, messageId)` 做全局幂等；增加重试、退避、死信、回放和人工重投。
5. 实现跨站 E2E：User A → Connecter A → Host → Connecter B → Runner/WP B → 原路结果返回，并覆盖断网、重复、乱序、目标离线和 Host 重启。

### P3：生产安全与运维

1. Connecter↔Host 使用 mTLS 或设备身份签名；token 仅用于 bootstrap，支持轮换与吊销。
2. 每个站点、群、主体和操作建立 ACL/Policy；Host 不应仅凭“在线”即可转发到任意群。
3. 统一 trace ID、结构化日志、投递时延、队列深度、离线时长、重试/死信指标。
4. 建立配置和 schema 兼容矩阵、滚动升级协议以及灾备演练。

### P4：达到规模后再做 Host HA（E4）

单 Host 成为真实 SLA 瓶颈后，再把目录/路由状态移至 PostgreSQL、etcd 或 Raft 支撑的控制面；消息队列可独立使用成熟 broker。不要用 Raft 复制 WorkPanel 群聊正文，也不要在规模尚小时先引入多 Host 共识复杂度。

## 建议的近期三个里程碑

1. **M1：Runner 不因崩溃卡死**——lease/ack/requeue + 故障恢复测试。
2. **M2：全局目录契约冻结**——site/subject/membership/capability ID 与审批凭证模型。
3. **M3：两站联邦最小闭环**——两台 Site Connecter 加一台 Host，真实消息与结果往返、断线恢复和幂等全部验收。

## 证据来源

本地源码证据（仓库 `D:\AI\workpanelConnecter`，commit `e5b51eb9f89f9bcbb19480d58dc2de230d7e7591`）：

- `src/relay/server.js`：HTTP 路由；Host 只有 peer register/heartbeat/list。
- `src/relay/hostJoin.js`、`hostPeers.js`：Connecter 出站加入 Host、心跳与 TTL 成员表。
- `src/relay/runners.js`、`delivery.js`：Runner 注册、TTL、串行 poll、result 与 WP best-effort 回写。
- `src/relay/schema.sql`、`db.js`：SQLite/WAL、消息/运行/Runner/Peer 数据模型和进程内串行写。
- `src/workpanelClient.js`、`src/relay/handlers.js`：User/群/消息通过 WorkPanel API 代理。
- `docs/CONNECTER-EVOLUTION.md`、`docs/superpowers/specs/2026-08-19-connecter-host-naming-design.md`：已拍板的站点/Host 边界与 E3/E4 路线。

验证命令：

```text
npm run test:host-peers       # HOST_PEERS_UNIT_OK
npm run test:runner-handler   # RUNNER_HANDLER_UNIT_OK
npm run test:runner           # RUNNER_GATE_OK
npm run test:relay-unit       # RELAY_UNIT_OK
```

## 证据边界

- 本报告是对上述 commit 的源码、文档和本机自动化测试评审。
- 没有部署三台真实服务器，也没有进行真实跨站闭环；由于源码中不存在 Host 消息数据面，不能将 peer 注册成功解释为跨站通信成功。
- 未在本轮修改 `workpanelConnecter` 业务代码。
