# WorkPanelConnecter 设计理念与演进路线

日期：2026-08-22
研究对象：`linlisWorkTeam/workpanelConnecter` v0.2.3 候选，基线 commits `b133877`, `12ebb66`, `d73e5c6`
证据：源码、发布门禁、真实 WorkPanel canary 与故障注入；详见 notes。

## 产品边界

```text
WorkPet/User -> Site Connecter A -> Connecter Host -> Site Connecter B -> Runner/Agent
                    |                                      |
                WorkPanel A                           WorkPanel B

站内消息不经过 Host；跨站消息必须经过 Host。
```

- WorkPet 是 UI，只连接所属站点的 Connecter。
- Connecter 是站点边缘网关，拥有本地身份投影、WorkPanel 适配、Runner 调度、持久 inbox/outbox 和策略执行。
- Connecter Host 全网一台，只接受已配置的 Site peer，维护全局目录投影并中继跨站消息；不直接接 WorkPet、WorkPanel 或 Runner。
- WorkPanel、Clowder、CLI Harness 都是可替换的应用/运行时适配器，不是联邦核心。

## 设计理念

1. **本地优先、故障隔离**：Host 不可用时，两边站点的本地 WorkPanel 和 Runner 路径仍应工作。
2. **中心化路由，不中心化执行**：Host 决定跨站转发和全局目录视图，但任务执行与业务数据尽量留在目标站点。
3. **稳定身份优先于显示名**：跨站只使用 Subject ID 与 canonical GroupRef；同名 Agent 必须显式消歧。
4. **消息先持久化再确认**：Runner 和 federation 都采用 lease、fencing、幂等键、TTL、重试和 first-terminal-wins。
5. **默认拒绝**：策略覆盖 origin/target/group/subject/operation/direction/capability/data classification；显式 deny 优先。
6. **协议与实现解耦**：HTTP handler、application service、目录、队列、WorkPanel/Runner 适配层分别演进。
7. **证据分级**：进程健康不等于端到端完成；本地 mock、真实 canary、真实多机和长稳测试分别报告。

## v0.2.3 候选现状

- P0：12 个顺序 migration、checksum、升级前备份与事务回滚；Runner lease/ack/renew/fencing/recovery；稳定标识和服务边界。
- P1：Directory v2、TTL presence、v1/v2 Runner 隔离、一次性 enrollment、设备凭证、解释型路由与同名消歧。
- P2：Host/Site durable inbox/outbox、命令/结果往返、Host 丢库重建、各节点独立重启/离线、WorkPanel 回写。
- P3：消息签名、外部密钥、HTTPS/mTLS client、临时 CA 的真实握手与无 client cert 拒绝、全维 ACL、运行时 policy 与 peer credential 生命周期、配额、审计、trace、备份恢复和 runbook。
- Windows 交付：WorkPet NSIS 安装 EXE、Connecter SEA 自包含包、SHA-256；全文档审查与 `test:docs` 将发布门禁扩展到 51 项。

## 演进路线

### P4：生产部署闭环（下一优先级）

- 两台真实 Site 服务器 + 独立 Host，启用 CA 验证和双向 TLS。
- 外部 secret store、证书/peer/signing key 轮换演练。
- 72 小时 soak、真实告警接收器、SLO 和故障复盘模板。
- 发布/回滚自动化与数据库备份恢复演练。

退出条件：真实跨机 command/result、网络分区恢复、证书轮换和 Host 恢复均有可重复证据。

### P5：协议与生态适配

- 把 WorkPanel、Clowder、A2A、ACP/CLI 适配器放在明确的 northbound/southbound ports 后面。
- A2A adapter 先支持 `tasks/send`，再支持异步状态、流式、取消和 Agent Card。
- 能力 schema 与 Directory 投影版本化；建立 adapter conformance kit。

### P6：规模化与高可用

- 先用生产指标确定 SQLite/单 Host 的真实瓶颈，再选择 PostgreSQL、外部队列、Temporal/Dapr 或 Host HA。
- 不应在没有吞吐、延迟和恢复目标前直接引入 Raft。若要多 Host，成员/领导权和消息数据面应分离设计。
- 支持区域/租户分片、目录缓存、策略分发和兼容窗口。

## 明确不做

- Connecter 不承担模型推理、Agent prompt 编排、长期团队记忆或 WorkPanel 业务逻辑。
- WorkPet 不发现全网节点，也不直连 Host。
- Host 不成为远程 shell，不直接执行 Runner 任务。
- 不以“所有流量都穿 Host”牺牲站点自治。

## 证据边界

当前候选基线已验证本机三进程、真实 WorkPanel `:8082`、本地真实 mTLS 握手和 Windows 产物构建/进程冒烟，但没有验证真实多服务器网络/证书运维、72 小时稳定性、外部告警或透明桌宠在每台目标机器上的可见效果。上述 P5/P6 是路线建议，不代表已实现。
