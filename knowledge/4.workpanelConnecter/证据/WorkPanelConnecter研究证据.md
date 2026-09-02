# WorkPanelConnecter 研究证据

日期：2026-08-22

## 来源版本

- WorkPanelConnecter：`b133877`（P0–P3）、`12ebb66`（mTLS Gate）、`d73e5c6`（v0.2.2 Windows 产物）、`8b176cb`（v0.2.3 文档审计）。
- 实施前的 WorkPanel 基线：`e5b51eb9f89f9bcbb19480d58dc2de230d7e7591`。
- Clowder AI：`8fd4824cb7db9124a0d863ba1b085a59b865c722`，提交时间 `2026-08-21T08:29:45Z`。
- wpKnowledge 基线：`d5d7a29ac1c1885eb07f81f1c53ffb595c1e1108`，另有此前已存在的本地调研改动。

## 本地证据

- v0.2.2：`npm run test:release-local` 输出 `RELEASE_LOCAL_GATE_OK gates=50`；v0.2.3 增加 `test:docs`，并于 2026-08-22 通过 `RELEASE_LOCAL_GATE_OK gates=51`。
- v0.2.3 发布地址：<https://github.com/linlisWorkTeam/workpanelConnecter/releases/tag/v0.2.3>。
- GitHub Actions 运行 `32518030659` 成功完成，并用独立构建的产物替换了最初的本地上传版本。
- `WorkPet_0.2.3_x64-setup.exe` 最终发布产物的 SHA-256 为 `dd419e65439d7ec5743f2e442d151943f55d02555f6e09fa692bb98426e02b3d`。
- `WorkPanelConnecter_0.2.3_win-x64-portable.zip` 最终发布产物的 SHA-256 为 `15f3a7fb32e0231956c5187791a7222daf875415fbf9603e10f5b5cba822f930`。
- `npm run test:mtls-handshake` 输出 `MTLS_HANDSHAKE_E2E_OK`：临时 CA 签发服务端和客户端证书，未携带客户端证书的请求会在进入 handler 前被拒绝。
- 使用 `CONNECTER_CANARY_URL=http://127.0.0.1:8082`、Group `seed-group-workpanel` / `LinlisWorkPanel` 执行 `npm run test:e2-canary`，输出 `E2_AT_MENTION_OK`。
- `node scripts/federation-soak.js --duration-ms=600000` 退出码为 0，输出 `FEDERATION_SOAK_OK`，耗时 602.4 秒。
- `node scripts/federation-soak.js --duration-ms=480000` 退出码为 0，输出 `FEDERATION_SOAK_OK`，耗时 482.6 秒。
- JavaScript 语法检查和暂存差异检查均通过；被忽略的 `config/relay.json` 与 `data/` 没有提交。

## 外部来源命令

- `gh api repos/zts212653/clowder-ai`
- `gh api repos/zts212653/clowder-ai/commits/main`
- `gh api repos/zts212653/clowder-ai/git/trees/main?recursive=1`
- `gh api repos/zts212653/clowder-ai/contents/<path> -H 'Accept: application/vnd.github.raw+json'`
- 通过 GitHub 仓库 API 查询 LangGraph、CrewAI、AutoGen、OpenAI Agents SDK、A2A、Temporal、Dapr、Clowder 和 OpenClaw 的元数据。

## 网络情况

- 最初的 `git fetch` 连接被重置，随后 WorkPanelConnecter 与 wpKnowledge 均成功获取远程内容。
- 两次克隆 Clowder 都因 `github.com:443` 暂时不可达而失败。GitHub API 读取成功，因此报告引用不可变 commit 链接，并明确不据此声称运行时已经验证。

## 尚未验证

- 没有执行 Clowder 的构建、测试、Redis 运行时或 UI。
- 没有发送真实的 Connecter 与 Clowder 之间的请求。
- 没有完成真实多服务器的 Connecter mTLS 部署或 72 小时 soak。
- 没有对竞品性能、企业支持或安全性做基准测试。

<details lang="en">
<summary>English summary</summary>

This record identifies the exact source revisions, local release gates, artifact hashes, mTLS test, canary, and federation soaks used by the WorkPanelConnecter research. Clowder runtime integration, real multi-server deployment, the 72-hour soak, and competitor benchmarks were not performed.

</details>
