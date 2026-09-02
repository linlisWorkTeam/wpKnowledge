---
date: 2026-09-01
topic: ohmyworkpanel-self-marketing-evidence
status: research-notes
---

# ohMyWorkPanel Self-Marketing 调研证据

## 仓库与版本

- 本地仓库：`D:\AI\LinlisWorkPanel`
- origin：`https://github.com/linlisWorkTeam/ohMyWorkPanel.git`
- 本地分支：`bugfix/v2.1.2`
- 本地 commit：`cfef082d7a9e5d434777374bd6b99ef8cd309cfc`
- 本地工作区：调研开始时 clean
- GitHub `main`：`b1af2659aea5068643729ee995bb944bf27b7a37`
- GitHub 最新 Release：`v2.1.2`，发布于 2026-08-24

GitHub `main` 比本地多 PR #16。该 PR 的主体是目录领域化和 AI contribution harness，并声明保留既有运行时契约；报告对核心能力的判断来自本地可核验源码，不把 PR 文案当作功能实现证据。

## 已执行的只读检查

```text
git status --short --branch
git remote -v
git rev-parse HEAD
git log -8 --date=short --pretty=format:...
git blame -L ... -- src-tauri/src/scheduler.rs
git blame -L ... -- src-tauri/src/commands.rs
git blame -L ... -- src-tauri/src/db.rs
git blame -L ... -- src-tauri/src/workflow.rs
git blame -L ... -- src-tauri/src/orchestrator.rs
git blame -L ... -- src-tauri/src/context_seams.rs
git blame -L ... -- src-tauri/src/wiki_context.rs
git blame -L ... -- src-tauri/src/git_inspect.rs
gh pr view 16 --repo linlisWorkTeam/ohMyWorkPanel ...
gh release view v2.1.2 --repo linlisWorkTeam/ohMyWorkPanel ...
```

## 关键源码定位

| 路径 | 行 | 观察 |
|---|---:|---|
| `src-tauri/src/models.rs` | 1–282 | Group、Member、Message、TaskRun、ExecutionContext；TaskRun 已有 parent/depth/review |
| `src-tauri/src/db.rs` | 103–158 | groups/messages/task_runs/run_events/message_attachments 基础表 |
| `src-tauri/src/scheduler.rs` | 402–482 | announcement/epitaph/live/memory/wiki/experience 统一注入并记录 ledger |
| `src-tauri/src/scheduler.rs` | 523–575 | chatbot 独立 fast path，说明营销 Writer 应使用 CLI Agent 而非 chatbot |
| `src-tauri/src/scheduler.rs` | 682–727 | CLI adapter 在安全解析的 cwd 中运行 |
| `src-tauri/src/scheduler.rs` | 1102–1205 | reviewer 与 awaiting_review 状态 |
| `src-tauri/src/scheduler.rs` | 1241–1296 | A2A @mention 委派和 depth 限制 |
| `src-tauri/src/commands.rs` | 463–603 | 用户消息、mentions、task run 创建、schedule_group |
| `src-tauri/src/commands.rs` | 1001–1050 | 人工 approved/rejected command |
| `src-tauri/src/memory.rs` | 3–19 | `.ohmyworkpanel` 本地运行目录 |
| `src-tauri/src/memory.rs` | 98–135 | Agent 工作区路径与越界控制 |
| `src-tauri/src/context_seams.rs` | 1–94 | epitaph 摘要和 context ledger |
| `src-tauri/src/wiki_context.rs` | 1–189 | Wiki retrieve fail-open |
| `src-tauri/src/git_inspect.rs` | 1–237 | 当前 Git 读取仅有 tag/head/20 commit subject |
| `src-tauri/src/workflow.rs` | 1–124 | ProjectVersion/Wave 表与 DTO |
| `src-tauri/src/workflow.rs` | 445–650 | Ask、Wave、awaiting_release 状态 |
| `src-tauri/src/orchestrator.rs` | 1–228 | 现有窄域串行 orchestrator 模式 |
| `src/components/furniture.tsx` | 341–384 | review queue 和批准/拒绝按钮 |

## 关键观察

1. 工作区读取能力存在，但“项目事实快照”不存在。
2. Git 读取存在，但信息量不足以直接支持可靠宣传：缺 README/CHANGELOG、diff、PR、changed docs 和证据引用。
3. 多 Agent 调度、A2A、review 和群聊 UI 可以直接复用。
4. 现有 reviewer 可能自动改变父 run 状态；Self-Marketing 最终批准必须单独建 campaign decision，不能委托给 Reviewer Agent。
5. `.ohmyworkpanel/` 已在项目 `.gitignore` 中，适合导出运行证据，不适合存需要团队版本控制的 Brand Guide。
6. 当前 `main` 已采用领域目录；新业务应放 `src/marketing/` 与 `src-tauri/src/marketing/`，而不是继续扩大根级 `scheduler.rs`、`web.rs`、`db.rs`。

## 外部资料

- [ohMyWorkPanel](https://github.com/linlisWorkTeam/ohMyWorkPanel)
- [PR #16](https://github.com/linlisWorkTeam/ohMyWorkPanel/pull/16)
- [v2.1.2 Release](https://github.com/linlisWorkTeam/ohMyWorkPanel/releases/tag/v2.1.2)
- [GitHub Commit API](https://docs.github.com/en/rest/commits)
- [GitHub Pull Request API](https://docs.github.com/en/rest/pulls)
- [GitHub Release API](https://docs.github.com/en/rest/releases)
- [GitHub Webhooks](https://docs.github.com/en/webhooks/about-webhooks)

## 未确认事项

- 没有对所有目标平台的当前发布 API 与账号权限做专项调研，因为 MVP 明确不自动发布。
- 没有运行模型生成质量 benchmark；schema、validator 和 golden fixture 属于建议实现。
- 没有验证 `gh` 在 ohMyWorkPanel 的所有目标部署环境均可用，因此 GitHub Provider 被定义为 optional/fail-open。
- 没有修改 ohMyWorkPanel 源码、数据库或运行服务。
