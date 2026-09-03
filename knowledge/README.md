# 知识库

`knowledge/` 是 wpKnowledge 的主体，保存研究、设计、作者笔记、旧知识卡片和经过脱敏的运行证据。目录按主题域组织，详细登记见 [知识库目录](知识库目录.md)。

## 主题域

| 路径 | 内容 | 入口 |
| --- | --- | --- |
| `1.dshAnalysis/` | DSH 分析 | [README](1.dshAnalysis/README.md) |
| `2.wiki/` | 通用研究、飞轮设计和方案材料 | [README](2.wiki/README.md) |
| `3.workpanel/` | WorkPanel 架构、调研和证据 | [README](3.workpanel/README.md) |
| `4.workpanelConnecter/` | Connecter 设计与证据 | [README](4.workpanelConnecter/README.md) |
| `5.ohMySocialPanel/` | ohMySocialPanel 专题 | [README](5.ohMySocialPanel/README.md) |

`inbox/`、`drafts/`、`concepts/`、`history/`、`runtime/` 与 [旧索引](index.md) 是历史 Knowledge Flywheel 留下的内容。它们现在只用于迁移和追溯，不是仍在 Git 中运行的状态机，也不会自动获得新平台的 `VERIFIED` 权限。

新的摄取、评测、Gate、发布和查询流程在 [domain-knowledge](https://github.com/linlisWorkTeam/domain-knowledge) 运行。适合人阅读和评审的知识或脱敏证据可以通过 PR 回到本仓；SQLite、CAS、Checkpoint 和完整运行日志继续留在运行环境。

## 添加内容

1. 选择最接近的主题域和内容分类，不确定时先更新 `知识库目录.md`。
2. 写明来源、日期、适用版本和仍待验证的部分。
3. 证据只保留复查结论所需的信息，并先完成脱敏。
4. 更新对应 README 或索引，让读者不靠全仓搜索也能找到新内容。

完整评审规则见根目录[贡献指南](../CONTRIBUTING.md)。
