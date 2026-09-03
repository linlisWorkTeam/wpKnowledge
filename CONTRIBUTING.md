# 贡献指南

感谢你为 wpKnowledge 补充知识。这个仓库只接收可阅读、可追溯、可通过 Git 评审的内容；Knowledge Flywheel 的代码和产品能力在 [domain-knowledge](https://github.com/linlisWorkTeam/domain-knowledge) 维护。

<details lang="en">
<summary>English summary</summary>

wpKnowledge accepts reviewed knowledge, research, design material and redacted evidence. Runtime code, specifications, tests, CLI, API and Console changes belong in domain-knowledge. Keep sources traceable, distinguish facts from inference, and remove secrets or personal data before opening a pull request.

</details>

## 先确定改动归属

| 内容 | 提交位置 |
| --- | --- |
| 研究、设计、作者随笔、知识卡片 | `knowledge/` 对应主题目录 |
| 已脱敏的真实运行记录、截图、报告 | 对应项目的 `证据/` 目录 |
| Knowledge Flywheel 代码、Spec、测试、部署和产品页面 | [domain-knowledge](https://github.com/linlisWorkTeam/domain-knowledge) |

不要在本仓重新建立 `endlessWpKnowledgeRunner/`、`src/`、`specs/`、`tests/`、`apps/`、`packages/` 或前台站点。跨仓库特性可以拆成相互链接的两个 PR：运行时 PR 证明行为，知识 PR 保存适合长期阅读的结果。

## 写作和证据要求

- 文档以中文为主；面向外部读者的关键入口可用 `<details lang="en">` 增加简短英文摘要。
- 清楚区分源码事实、运行事实、外部资料和作者推断，不把路线图写成已实现能力。
- 外部结论附可核对来源；源码引用尽量指向固定 commit。
- 运行记录写明日期、版本、环境、命令、结果和限制，不能只给成功截图。
- 使用自然、具体的表达。少写口号，多写读者能复核的条件和结论。
- 更新目录或文件名时，同步修复入口文档和相对链接。

## 安全与隐私

提交前检查 staged diff，确认不含 API key、Bearer token、Cookie、外部 CLI 登录态、数据库、CAS、Checkpoint、完整模型对话或个人信息。日志和截图只保留证明结论所需的最小信息。发现安全问题时按 [SECURITY.md](SECURITY.md) 处理。

## Pull Request

一次 PR 尽量只处理一个主题，并说明：

- 为什么需要这份知识或证据；
- 来源、版本和可复查方法；
- 哪些是事实，哪些仍是推断；
- 是否关联 `domain-knowledge` 的实现 PR；
- 做过哪些链接、格式和敏感信息检查。

AI Agent 生成的内容和人工内容遵循同一标准。提交者需要读过最终文本，能解释结论，也愿意维护它。

提交贡献即表示你同意该贡献按仓库的 [MIT License](LICENSE) 发布；外部引用仍保留原有许可。
