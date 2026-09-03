# wpKnowledge

> 把知识、研究过程和运行证据留在 Git 里，让每个结论都有来处，也经得起复查。

<details lang="en">
<summary>English summary</summary>

wpKnowledge is the content repository for the Knowledge Flywheel. It stores reviewed knowledge, research notes, design material and redacted evidence. The executable runtime, LangGraph workflow, specifications, tests, API and Console live in [domain-knowledge](https://github.com/linlisWorkTeam/domain-knowledge).

</details>

[浏览知识库](knowledge/README.md) · [知识目录](knowledge/知识库目录.md) · [运行时项目](https://github.com/linlisWorkTeam/domain-knowledge) · [方案 PPT](knowledge/2.wiki/设计/当前wpKnowledge知识飞轮方案.pptx) · [参与贡献](CONTRIBUTING.md)

## 这个仓库保存什么

`wpKnowledge` 不再承载可执行的 Knowledge Flywheel。这里留下的是适合通过 Git 阅读和评审的内容：

- 研究资料、设计方案和作者随笔；
- 已脱敏的评测结果、运行记录与演示材料；
- 旧 OKF 卡片及其历史索引，供迁移和追溯使用；
- 知识格式、来源和维护约定。

Agent 编排、知识摄取、来源追踪、SQLite/CAS、评测 Gate、发布、DSH API、CLI、Web Console、Spec 和测试已经迁到 [domain-knowledge](https://github.com/linlisWorkTeam/domain-knowledge)。两边的分工很简单：`domain-knowledge` 负责“跑”，`wpKnowledge` 负责“留下可评审的知识与证据”。

## 从哪里开始

| 你想做什么 | 入口 |
| --- | --- |
| 浏览全部知识域 | [知识库说明](knowledge/README.md) |
| 查找某个主题 | [知识库目录](knowledge/知识库目录.md)与[知识索引](knowledge/index.md) |
| 阅读 Knowledge Flywheel 设计 | [方案文档](knowledge/2.wiki/设计/知识飞轮实现方案.md)与[方案 PPT](knowledge/2.wiki/设计/当前wpKnowledge知识飞轮方案.pptx) |
| 查看真实运行证据 | [WorkPanel 证据目录](knowledge/3.workpanel/证据/) |
| 运行或开发 Knowledge Flywheel | [domain-knowledge](https://github.com/linlisWorkTeam/domain-knowledge) |
| 提交知识、研究或证据 | [贡献指南](CONTRIBUTING.md) |

## 仓库地图

```text
wpKnowledge/
├── knowledge/                 # 知识、研究、设计和脱敏证据
│   ├── 1.dshAnalysis/         # DSH 专题
│   ├── 2.wiki/                # 通用研究与飞轮设计
│   ├── 3.workpanel/           # WorkPanel 研究与运行证据
│   ├── 4.workpanelConnecter/  # Connecter 专题
│   └── 5.ohMySocialPanel/     # ohMySocialPanel 专题
├── CONTRIBUTING.md            # 内容贡献与评审规则
├── SECURITY.md                # 脱敏和安全报告约定
└── LICENSE                    # MIT License
```

仓库根目录不再接收运行时代码、`package.json`、产品页面、Spec 或测试。涉及运行时行为的改动，请提交到 `domain-knowledge`；如果一次工作同时产生代码和知识证据，应分别建立两个 PR，并在描述里互相链接。

## 内容可信度

Git 中出现一份文档，不等于它已经通过 Knowledge Flywheel 发布。请根据内容标注区分：

- **研究或设计**：记录分析、取舍和待验证假设；
- **运行证据**：记录某次明确环境和版本下的事实；
- **旧 OKF 内容**：保留历史状态，但不继承新运行时的 `VERIFIED` 权限；
- **正式发布状态**：以 `domain-knowledge` 的 Registry、GateDecision 和 Publication 为准。

提交证据前请移除密钥、令牌、用户数据、外部登录态和不必要的绝对路径。运行时产生的 SQLite、CAS、Checkpoint 与完整日志不应进入本仓库。

## License

本仓库采用 [MIT License](LICENSE)。引用外部材料时，还应遵守原作者和原项目的许可要求。
