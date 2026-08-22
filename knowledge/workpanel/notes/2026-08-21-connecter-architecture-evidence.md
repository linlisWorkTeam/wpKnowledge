# WorkPanel Connecter 架构评审证据笔记

- 日期：2026-08-21
- 仓库：`D:\AI\workpanelConnecter`
- 分支：`main`
- commit：`e5b51eb9f89f9bcbb19480d58dc2de230d7e7591`
- 拉取结果：`git pull --ff-only origin main` → `Already up to date`

## 已确认

- WorkPet 正式命名已锁定；源码无 PanelPet 产品组件。
- Runner register/heartbeat/tasks/result 与 pet→runner 路由通过本机测试。
- Connecter→Host register/heartbeat/list 通过本机测试。
- Host 源码引用仅涵盖 peer registry；未找到 federation/forward/inbox/outbox 消息实现。
- `runner_tasks` 的 `dispatched` 状态无 lease/ack/超时重投字段和逻辑。
- `writeTx` 是单进程 Promise 串行写；schema 通过启动时直接执行 SQL 建立，无 migration version。

## 命令结果

```text
npm run test:host-peers       HOST_PEERS_UNIT_OK
npm run test:runner-handler   RUNNER_HANDLER_UNIT_OK
npm run test:runner           RUNNER_GATE_OK
npm run test:relay-unit       RELAY_UNIT_OK
```

## 未验证

- 未部署真实两站加 Host 拓扑。
- 未验证 Host 断网、Runner 取任务后崩溃、跨站重复/乱序和凭证轮换。
- 未运行依赖真实 canary WorkPanel 的门禁，避免把外部环境状态混入架构结论。

