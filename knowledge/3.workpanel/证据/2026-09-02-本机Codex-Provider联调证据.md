# 本机 Codex Provider 联调证据

日期：2026-09-02

## 关键发现

1. WorkPanel 外部 v5 数据库会跳过旧 provider 迁移，因此用 schema v6 幂等重放 v5。
2. Connecter Host 原先过滤 `/v2/dispatches`，且路由器未读取 Host 的 `federation_routes`。
3. Host 内 provider dispatch 不能假装 Host 是自己的 Site peer，应直接写入目标 Site 投递队列。
4. 回程事件必须保存原 `groupRef`；HMAC canonicalization 必须与 JSON 对 `undefined` 的省略一致。
5. 返回 Host 的 `run.event` 应使用原 dispatch 做精确关联并原子完成。
6. runner 原先遇到一次 poll 错误即退出，现已增加有上限的指数退避。

## 验证命令

```text
npm test
npm run test:relay-unit
npm run test:relay
npm run test:e2e-resume
npm run test:routes
npm run test:federation
npm run test:codex-runner-e2e
node scripts/workpanel-dispatch-api-unit.js
node scripts/federation-host-unit.js
node scripts/p3-security-unit.js
```

## 最终证明

```text
PROVIDER_E2E_OK
MEMBER_ID 88219888-3824-4c35-9170-82371e2f3c00
RUN_ID 97b7ba7f-a358-41d8-9115-ec550c23c1d5
DISPATCH_ID 9a6e81b9-ee59-53b6-bf7f-f0ff60736db8
REPLY_ID ca9e0033-f026-4ba3-9eb9-0c3086150ab6
REPLY_COUNT 1
MARKER WORKPANEL_PROVIDER_E2E_5f3c1630cb20|workpanel-connecter|0.2.3
WRITE_BACK false
```

## 未确认事项

- Windows 整机重启后的计划任务启动顺序尚未做破坏性验收。
- 长时间运行、多个远程 Site 竞争同名 Agent、Host 数据丢失恢复仍需独立测试。
