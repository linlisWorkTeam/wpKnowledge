# 本机 Codex 通过 Connecter Host 接入 ECS WorkPanel

日期：2026-09-02  
研究对象：`linlisWorkTeam/ohMyWorkPanel`、`linlisWorkTeam/workpanelConnecter`、Windows Codex CLI、阿里云 ECS canary

## 结论

本机 Codex 已能作为 `connecter-remote` provider 资源加入 ECS 上的 ohMyWorkPanel 测试群。真实验收覆盖 WorkPanel 创建任务、ECS Connecter Host 选择 Windows Site 路由、本机 runner 调用 Codex CLI、结果沿联邦链路返回 Host、WorkPanel 只落一条 Agent 回复。

相关 PR：

- [ohMyWorkPanel PR #18](https://github.com/linlisWorkTeam/ohMyWorkPanel/pull/18)
- [workpanelConnecter PR #8](https://github.com/linlisWorkTeam/workpanelConnecter/pull/8)

## 运行拓扑

```text
ECS ohMyWorkPanel canary :8081
  -> connecter-remote provider
  -> ECS Connecter Host :9080
  -> federation pull (Windows Site, NAT-friendly)
  -> Windows Connecter :9080
  -> codex-windows11 runner -> Codex CLI
  -> signed run.event -> ECS Connecter Host
  -> provider dispatch result -> WorkPanel Agent reply
```

WorkPet 绑定每站的 **Connecter**；全网调度中心称为 **Connecter Host**。本次使用 Site 注册、心跳/TTL、目录广播、路由和 pull/ack/result 协议，不是 Relay 静态 Agent 配置。

## 源码证据

### ohMyWorkPanel

- 本地仓库：`D:\AI\LinlisWorkPanel-connecter-provider-main`
- 验收提交：`c8c6917db028bc43f354aa30e796668d19464f8a`
- 关键能力：provider profile、远程成员配置、任务 dispatch/poll、schema v6 收敛迁移。
- CI：Build/test/Rust 与 Windows Tauri package 均通过。

### workpanelConnecter

- 本地仓库：`D:\AI\workpanelConnecter`
- 验收提交：`bf1d642685f02e2d05ab9d5370ab44d5dcf70504`
- 关键能力：Host 暴露受服务凭证保护的 `/v2/dispatches`；路由器纳入带 TTL 的 `federation_routes`；Host provider dispatch 直接进入目标 Site 投递队列；原始 `groupRef` 随结果返回；HMAC 规范化与 JSON 往返一致；Host 依据原 dispatch 的 Site、group、causation 与 provider subject 原子消费 `run.event`；runner 在 Relay 短暂不可用时退避重连。

## 真实验收

最终门禁输出 `PROVIDER_E2E_OK`：

- WorkPanel run：`97b7ba7f-a358-41d8-9115-ec550c23c1d5`
- Connecter dispatch：`9a6e81b9-ee59-53b6-bf7f-f0ff60736db8`
- WorkPanel reply：`ca9e0033-f026-4ba3-9eb9-0c3086150ab6`
- 回复数：`1`
- 证明串：`WORKPANEL_PROVIDER_E2E_5f3c1630cb20|workpanel-connecter|0.2.3`
- `writeBack=false`，由 WorkPanel provider 统一落库，避免双写。

本地通过 `npm test`、`test:relay-unit`、`test:relay`、`test:e2e-resume`、`test:routes`、`test:federation`、`test:codex-runner-e2e`。runner E2E 会故意让首次 task poll 返回 503，并验证自动恢复。

## 部署与自举

- ECS WorkPanel canary 运行 `c8c6917...`，systemd 服务健康，schema v6。
- ECS Connecter Host 运行 `bf1d642...`，systemd 服务健康。
- Windows 计划任务 `WorkPanelConnecter-Relay` 与 `WorkPanelConnecter-CodexRunner` 在登录时自动启动，异常退出后每分钟重试。
- ECS 到 GitHub 偶发超时；部署可使用经 `git bundle verify` 校验的最小增量包，并检出 PR 中同一个 Git 对象。

## 建议

1. PR 合并后把 canary 固定到合并提交并重跑同等门禁。
2. 将 provider token、Site peer token 和云访问凭证纳入 Secret 管理与轮换。
3. 对过期路由、outbox backlog、dispatch 超时和计划任务退出增加告警。
4. 在多 Host HA 前先稳定 register、heartbeat/TTL、membership、routing、poll/ack/result 契约。

## 证据边界

- 证明 ECS canary 与一台 Windows Site 的真实闭环，不代表生产已发布。
- 未验证多 Host 共识、跨地域故障切换、容量上限和长期 soak。
- 公网地址、token、云访问密钥、SQLite 数据和登录凭证均未写入 Git。
- 计划任务已注册，但尚未通过整机重启验收；异常 poll 自动恢复已由协议 E2E 验证。
