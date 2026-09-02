# OKF v1 卡片契约

旧版知识飞轮每个 Markdown 文件保存一个 concept。frontmatter 是机器控制部分，Markdown 正文供 Agent 和使用者阅读。

<details lang="en">
<summary>English summary</summary>

One Markdown file stores one concept. Frontmatter is machine-controlled; the body is human-readable. Callers may provide candidate content and provenance, but only the runner may write scores, timestamps or publication status.

</details>

必填字段：

- `schema_version`：以 `okf.v1` 开头。
- `name`：与文件名使用相同 slug，只能包含小写字母、数字、`-` 或 `_`。
- `sources`：已验证卡片至少要有一个来源。草稿可以暂时不完整，但缺少来源时不能通过发布 Gate。优先使用仓库相对路径，并附上 `lines`、`commit`、`url` 或 `pinned` 锚点。
- `status`：只能是 `draft` 或 `verified`，并与所在目录一致。
- `verified`：草稿为 `false`，已验证卡片为 `true`。
- `version`：正整数。新的已验证修订需要递增版本号。
- 非空 Markdown 正文。

Runner 持有 `score`、`confidence`、`score_breakdown`、时间戳和历史快照。调用方只能提交候选正文与来源，不能通过写文件自行选择发布状态。

> 迁移说明：这是旧 OKF 格式契约。当前 TypeScript Runtime 会把旧 `verified` 卡片导入为 `CANDIDATE`，直到新的行为证据和确定性 Gate 再次证明它可以发布。
