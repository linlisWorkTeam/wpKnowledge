# wpKnowledge

知识飞轮实现与受控知识库。

## 仓库边界

- `endlessWpKnowledgeRunner/`：飞轮运行时、CLI、DSH 适配层、Dashboard 与测试。
- `knowledge/`：统一管理的知识库；来源资料、OKF 卡片、草稿、已验证知识和历史版本都在这里。
- 新知识先进入 `knowledge/inbox/`，再由 `endlessWpKnowledgeRunner/fw.py ingest` 规范化、评分并写入受控区域。

目录职责、来源编号、分类和插入规则见 [`knowledge/知识库目录.md`](knowledge/知识库目录.md)；运行时写入约束见 [`endlessWpKnowledgeRunner/docs/KNOWLEDGE-REPOSITORY.md`](endlessWpKnowledgeRunner/docs/KNOWLEDGE-REPOSITORY.md)。

## 来源知识域

数字前缀用于稳定标识来源域，不代表优先级。文档文件名直接使用内容标题；研究日期保留在正文或元数据中，不再放在文件名中。

### 1.dshAnalysis

DeepSeek Harness（DSH）可借鉴性分析，作为 WorkPanel 机制样本，不等于把整个 DSH 接入飞轮。

- [DSH 可借鉴性分析报告](knowledge/1.dshAnalysis/调研/DSH可借鉴性分析报告.md)
- [DSH 反汇编调查](knowledge/1.dshAnalysis/调研/DSH反汇编调查.md)
- [DSH 白话图文版](knowledge/1.dshAnalysis/调研/DSH白话图文版.md)
- [DSH 插件化拆解](knowledge/1.dshAnalysis/调研/DSH插件化拆解.md)
- [DSH 插件化专业技术报告](knowledge/1.dshAnalysis/调研/DSH插件化专业技术报告.md)
- [DSH 分析任务书](knowledge/1.dshAnalysis/任务/DSH分析任务书.md)
- [DSH 分析过程笔记](knowledge/1.dshAnalysis/作者随笔/DSH分析过程笔记.md)

### 2.wiki

知识飞轮的设计、研究、知识格式、评测和检索资料，入口见 [`knowledge/2.wiki/README.md`](knowledge/2.wiki/README.md)。

- [设计文档](knowledge/2.wiki/设计/README.md)
- [研究材料](knowledge/2.wiki/研究/README.md)
- [脚本](knowledge/2.wiki/脚本/)

### 3.workpanel

LinlisWorkPanel 架构、实现分析、规划和调研证据。

- [综合架构分析](knowledge/3.workpanel/调研/LinlisWorkPanel综合架构分析.md)
- [WorkPanel 2.0.0 架构评审](knowledge/3.workpanel/调研/WorkPanel%202.0.0架构评审.md)
- [WorkPanel Connecter 愿景符合度与可扩展性评审](knowledge/3.workpanel/调研/WorkPanel%20Connecter愿景符合度与可扩展性评审.md)
- [endlessWpKnowledgeRunner 飞轮实现分析](knowledge/3.workpanel/调研/endlessWpKnowledgeRunner飞轮实现分析.md)
- [WorkPanel 架构调研笔记](knowledge/3.workpanel/作者随笔/WorkPanel架构调研笔记.md)
- [WorkPanel 调研任务书](knowledge/3.workpanel/规划/WorkPanel调研任务书.md)

### 4.workpanelConnecter

WorkPanelConnecter 的设计理念、演进路线、市场竞品、集成分析和证据。

- [综合分析报告](knowledge/4.workpanelConnecter/调研/WorkPanelConnecter综合分析报告.md)
- [设计理念与演进路线](knowledge/4.workpanelConnecter/调研/WorkPanelConnecter设计理念与演进路线.md)
- [市场竞品分析](knowledge/4.workpanelConnecter/调研/WorkPanelConnecter市场竞品分析.md)
- [与 Clowder AI 集成分析](knowledge/4.workpanelConnecter/调研/WorkPanelConnecter与Clowder%20AI集成分析.md)
- [研究证据](knowledge/4.workpanelConnecter/证据/WorkPanelConnecter研究证据.md)

## 运行

```powershell
cd endlessWpKnowledgeRunner
python fw.py status --json
python fw.py query --q connecter --no-feedback --json
```

前台 Dashboard 由 runner 提供；它消费 `knowledge/` 的运行时状态，不改变来源知识域的目录契约。
