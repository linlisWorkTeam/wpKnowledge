# 本机 Codex 经 Connecter 接入：证据与过程笔记

- 日期：2026-09-01
- 调研设备：Windows 11，`D:\AI\workpanelConnecter`
- 研究对象：WorkPanelConnecter、ohMyWorkPanel、本机 Codex CLI

## 源码快照

| 仓库 | 本机路径 | commit / 分支 |
| --- | --- | --- |
| WorkPanelConnecter | `D:\AI\workpanelConnecter` | `c81a177efa85d8c2d9ea368a1e6d9fe01eaf8025`，`main` |
| ohMyWorkPanel | `D:\AI\LinlisWorkPanel` | `cfef082d7a9e5d434777374bd6b99ef8cd309cfc`，`bugfix/v2.1.2` |
| wpKnowledge 基线 | `D:\AI\wpKnowledge-codex-runner-research` | `6999099`，由 `origin/main` 建独立 worktree |

原 `D:\AI\wpKnowledge` 工作树位于 `codex/ohmyworkpanel-style-consistency`，存在用户未提交修改。本次没有切换或修改该工作树。

## Connecter 证据

1. `docs/protocol/runners.md`：Runner 只出站；register、heartbeat、poll、ack、renew、result；默认 TTL 60 秒；租约 fencing；生产可要求设备凭证。
2. `src/relay/runners.js`：预配或 enrollment credential 注册；Runner 投影进 Directory；任务领取受 max concurrency、lease 和 heartbeat 约束；result 幂等。
3. `src/relay/services/dispatchService.js`：Directory v2 可把目标解析到本站或异站 Runner；异站经 federation outbox。
4. `src/relay/handlers.js:440-488`：当前 Runner 路由只在 pet chat 分支中被调用，context 仍写为 `pet-chat`。legacy ops chat 会直接调用 WorkPanel，不会进入 Runner。
5. `src/relay/handlers/directoryHandlers.js`：Directory subjects/endpoints 和 route explain 只允许 ops 身份。
6. `src/workpanelClient.js:443-464`：Runner 结果可 best-effort 以同名 Agent 成员身份写回 WorkPanel；前提是群内已经存在匹配的 active agent member。
7. `GET /v1/runs/:id` 当前返回 `runs` 行，Runner result 正文位于 `detail_json`；这可支撑 POC 轮询，但不是稳定的 WorkPanel provider 契约。

## ohMyWorkPanel 证据

1. `src-tauri/src/adapters/codex.rs` 已能在 **ohMyWorkPanel 所在主机** spawn `codex exec --json`，但默认强制走本机 `:18888` DeepSeek-compatible shim；这不是“使用另一台设备现有 ChatGPT 登录态”的远端资源接入。
2. `src-tauri/src/adapters/manifest.rs` 的 manifest 只接收 `{prompt}`、`{model}`、`{session}` 等 argv 占位符；调度入口仍是本机 spawn。它不能直接表达远端 subject、groupRef、lease、在线状态和取消传播。
3. `src-tauri/src/adapters/manifest.rs:336-346` 只有 Cursor 和声明了 resume flag 的 manifest 持久化 session；内置 Codex 当前不持久化 session。
4. `src-tauri/src/web.rs` 添加 Agent 时会解析本地 adapter，并写入本地 `agent_profiles`。源码中没有 Connecter Directory client 或远端 Agent provider。
5. `src-tauri/src/adapters/chatbot.rs` 的 custom chatbot 是 30 秒同步 OpenAI-compatible HTTP completion；不适合分钟级、可改文件、需取消和租约续期的 coding agent。

## 本机 Codex 证据

只读命令：

```text
codex --version
codex --help
codex exec --help
codex exec resume --help
codex app-server --help
codex login status
codex doctor
```

观察：

- 已安装 `codex-cli 0.144.6`。
- `codex exec --json` 提供 JSONL；支持 `-C/--cd`、sandbox、approval policy、output schema、ephemeral。
- `codex exec resume <SESSION_ID> <PROMPT> --json` 可恢复会话。
- `codex app-server`、`exec-server` 和 remote-control 在该版本仍标记 experimental，不适合作为首版稳定依赖。
- `codex login status` 显示 `Logged in using ChatGPT`；`codex doctor` 的脱敏报告显示 auth 已配置、没有存储 API key。
- `codex doctor` 因当前非交互 `TERM=dumb` 返回 1，但安装、配置、auth、状态数据库均为健康；没有执行真实模型调用。
- update probe 超时，故不能声称 0.144.6 是 2026-09-01 的最新版本。

## 现场门禁

2026-09-01 在 `D:\AI\workpanelConnecter` 执行：

```text
npm run test:runner          -> RUNNER_GATE_OK
npm run test:directory-api   -> DIRECTORY_API_UNIT_OK
npm run test:federation-e2e  -> FEDERATION_E2E_OK
```

这些门禁验证了模拟 Runner/Directory/Federation 协议，不等于本机 Codex 已被 ohMyWorkPanel 实际调度。

## 外部资料边界

按 OpenAI Docs 路径尝试检索和抓取 Codex CLI non-interactive、SDK、app-server 文档。当前内置网页检索没有返回页面内容，`developers.openai.com` 直连返回 HTTP 403。因此 Codex 命令能力以本机 0.144.6 的实际 `--help` 和 `doctor` 为证据，官方页面仅保留为后续复核入口：

- <https://developers.openai.com/codex/cli/reference/>
- <https://developers.openai.com/codex/app-server/>

## 未验证事项

- 未运行一次真实 `codex exec`，未消耗用户额度。
- 未创建 Codex Runner 代码、设备凭证或生产配置。
- 未让 ohMyWorkPanel 的真实 UI 发现或调度本机 Codex。
- 未做真实双 Site + 独立 Connecter Host 部署。
- 未验证 Codex CLI 版本升级后的 JSONL 事件兼容性。
