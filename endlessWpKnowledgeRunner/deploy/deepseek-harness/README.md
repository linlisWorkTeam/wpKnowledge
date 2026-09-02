# DeepSeek Harness 部署

这个目录保存知识飞轮调用 DeepSeek Harness 时使用的无密钥配置。Harness 是 Agent 执行基础设施；知识版本、评测、Gate 和发布仍由 wpKnowledge 持有。

<details lang="en">
<summary>English summary</summary>

This deployment runs DeepSeek Harness as a process-based AgentProvider. Credentials stay in environment variables, while wpKnowledge remains authoritative for knowledge governance and publication.

</details>

## 本地最小验证

官方 Harness 仍处于开发者预览阶段，因此版本必须固定。`opencode-go.cordis.yml` 使用 OpenCode Go 的 OpenAI 兼容端点和 DeepSeek V4 Flash；`provider.cordis.yml` 是备用的 Anthropic Messages 兼容配置。任何密钥都不得写入仓库。

```bash
export DSH_HOME="$PWD/.workpanel/dsh"
export DSH_TELEMETRY_MODE=DISABLED
export DSH_PERMISSION_MODE=read-only
export OPENCODE_GO_API_KEY='<token>'
export WP_DSH_MODEL=deepseek-v4-flash

npx --yes @deepseek-ai/dsh@0.1.2-alpha.4 \
  --profile headless \
  --patch "$PWD/endlessWpKnowledgeRunner/deploy/deepseek-harness/opencode-go.cordis.yml" \
  '只输出 {"ok":true}'
```

## 接入知识飞轮

```bash
export WP_FLYWHEEL_AGENT_PROVIDER=deepseek-harness
export WP_DSH_COMMAND=npx
export WP_DSH_ARGS_JSON='["--yes","@deepseek-ai/dsh@0.1.2-alpha.4","--profile","headless","--patch","/absolute/path/opencode-go.cordis.yml"]'
export WP_DSH_ALLOWED_ROOTS='/absolute/path/wpKnowledge:/absolute/path/ohMyWorkPanel'
export WP_DSH_TIMEOUT_MS=600000

npm run knowledge -- workflow-run --repository /absolute/path/ohMyWorkPanel
```

Provider 对最终 stdout 执行 JSON 解析和调用方 Schema 校验。Prompt 正文不会写入审计日志；日志只保存 SHA-256、角色、Run/Node 关联、耗时、退出状态和错误分类，位置为 `.workpanel/demo/agent-runs.jsonl`。Harness 自己的完整 Session 日志位于显式 `DSH_HOME` 下。

Headless CLI 当前把 Prompt 作为 argv 传递，同权限宿主进程可能读取。不要在 Prompt 中放凭据；生产化前应改用 DSH SDK 或 stdin/受保护 IPC。2026-09-02 的完整实跑记录见 [`knowledge/3.workpanel/证据/2026-09-02-DeepSeek-Harness真实Agent治理演示.md`](../../../knowledge/3.workpanel/证据/2026-09-02-DeepSeek-Harness真实Agent治理演示.md)。

## 公网演示界面

`web-public.cordis.yml` 把 WebServer 绑定到 `0.0.0.0`。Harness 会输出一次性认证 URL；首页用该 URL 换取签名 Cookie，普通未认证请求返回 401。启动时必须把公网 authority 加入 trusted host：

```bash
export WP_DSH_WEB_PORT=3080
npx --yes @deepseek-ai/dsh@0.1.2-alpha.4 web \
  --patch "$PWD/endlessWpKnowledgeRunner/deploy/deepseek-harness/opencode-go.cordis.yml" \
  --patch "$PWD/endlessWpKnowledgeRunner/deploy/deepseek-harness/web-public.cordis.yml" \
  --trusted-host '<公网 IP>:3080' \
  --no-open
```

认证 URL 等同管理员凭据，不得写入仓库、日志示例或截图。当前配置没有 TLS，只用于短期演示；长期部署必须在前面增加 HTTPS 反向代理和独立身份认证。

## 安全边界

- 自动治理使用 `read-only` Harness 权限；生成代码通过 JSON Artifact 返回，不允许 Agent 直接修改受治理仓库。
- `WP_DSH_ALLOWED_ROOTS` 是部署方白名单。来自 HTTP 请求的仓库路径仍需通过这层真实路径校验。
- 当前 ProjectEvaluator 只能运行受信项目命令。完成 hostile-code 沙箱前，不要向任意公网用户开放工作流启动权限。
- DeepSeek Harness Web 自身不提供可直接暴露公网的 TLS 或通用登录层；公网部署应放在带认证的反向代理之后。
