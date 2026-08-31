# Knowledge Base

`knowledge/` 是统一受控的知识库。来源资料按编号和内容分类保存，飞轮运行区负责把新材料变成可检索的 OKF 知识卡。

## 来源域

完整登记和插入规则见 [`知识库目录.md`](知识库目录.md)。

| 路径 | 内容 | 入口 |
|---|---|---|
| `1.dshAnalysis/` | DSH 分析 | [`README.md`](1.dshAnalysis/README.md) |
| `2.wiki/` | 飞轮设计与外部研究 | [`README.md`](2.wiki/README.md) |
| `3.workpanel/` | WorkPanel 架构与实现知识 | [`README.md`](3.workpanel/README.md) |
| `4.workpanelConnecter/` | Connecter 设计与证据 | [`README.md`](4.workpanelConnecter/README.md) |

来源域内部统一采用内容分类目录；文档使用内容标题命名，日期写在正文或元数据中。

## 飞轮运行区

| 路径 | 职责 | 写入者 |
|---|---|---|
| `inbox/` | 待摄取的原始 Markdown | 人工或采集适配器 |
| `drafts/` | 未通过门禁的 OKF 卡片 | runner |
| `concepts/` | 已验证、可检索的卡片 | runner |
| `history/<name>/` | 已发布卡片的不可变版本 | runner |
| `schema/` | 卡片格式和治理契约 | 维护者 |
| `index.md` | 卡片和来源索引 | runner |
| `runtime/` | 反馈、日志和 liveMode 游标 | runner |

新来源内容先进入 `inbox/` 或其他明确的 Git 评审目录，再通过 `npm run knowledge -- ingest` 提交为候选。候选正文进入内容寻址存储，状态、事件、评分、反馈和发布指针进入本地 SQLite Registry。

`concepts/`、`drafts/`、`history/` 和 `runtime/` 是旧 `endlessWpKnowledgeRunner` 留下的迁移来源，不再是新运行时的可写状态机。旧卡片可使用 `npm run knowledge -- migrate-legacy --root knowledge` 幂等导入，但历史 `verified` 只记录为 legacy metadata，不继承新平台的发布权限。

新架构与迁移契约见 [`docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md)和 [`docs/MIGRATION.md`](../docs/MIGRATION.md)。
