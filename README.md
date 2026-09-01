# wpKnowledge

知识飞轮平台、可验证知识注册表与研究知识库。

## 仓库边界

- `endlessWpKnowledgeRunner/`：Knowledge Flywheel 的完整组件根目录，包含应用入口、领域/应用/适配器代码、产品控制台、Spec、验收 fixture、测试和运维文档。
- `knowledge/`：研究资料和旧 OKF 卡片的 Git 可评审来源；不再充当运行时状态数据库。
- `mvp-flywheel/`：历史 Python MVP，仅用于对照，不是当前 TypeScript Flywheel 的运行入口或规范事实源。

目录职责、来源编号、分类和插入规则见 [`knowledge/知识库目录.md`](knowledge/知识库目录.md)。当前组件入口见 [`endlessWpKnowledgeRunner/README.md`](endlessWpKnowledgeRunner/README.md)，规范见 [`endlessWpKnowledgeRunner/specs/README.md`](endlessWpKnowledgeRunner/specs/README.md)，运行时架构见 [`endlessWpKnowledgeRunner/docs/ARCHITECTURE.md`](endlessWpKnowledgeRunner/docs/ARCHITECTURE.md)。

## 信任语义

候选知识先经过确定性文档质量门禁，但质量合格不会自动成为 `VERIFIED`。只有独立评测器提交的 `EvaluationReport` 绑定完整性可校验的执行证据，并通过确定性 Publication Gate 后，系统才能用幂等 publication key 发布知识。仓库现已提供固定 commit 的受信项目 EvalRunner：它在临时 `git archive` 工作区执行白名单工具并记录命令、版本、退出码和截断输出；它不是敌对代码沙箱，不能外推为不可信 C++ 的生产隔离证明。

旧 `endlessWpKnowledgeRunner` 的 Python 实现已被移除；该目录现在是完整 TypeScript Flywheel 组件，而非兼容文件夹。`fw.mjs` 只把仍受支持的 init、ingest、query、get、status、scan 和 feedback 命令委派给组件内同一个 CLI、SQLite Registry 与 CAS。旧状态机、自制 YAML 解析器、Python shell 桥接、动态 DSH 插件和“文档分数即 verified”语义不再存在；score、eval 和 harvest 会明确拒绝，避免形成第二套事实源。

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

- [设计文档索引](knowledge/2.wiki/README.md)
- [研究材料](knowledge/2.wiki/研究/README.md)
- [脚本](knowledge/2.wiki/脚本/)

### 3.workpanel

LinlisWorkPanel 架构、实现分析、规划和调研证据。

- [Knowledge Flywheel PR #11 交付与全项目测评](knowledge/3.workpanel/调研/2026-09-01-PR11知识飞轮交付测评.md)
- [WorkPanel 调研长期综合入口](knowledge/3.workpanel/调研/WorkPanel综合分析报告.md)
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
npm install
npm test
npm run validate:specs

# 固定 commit 的 ohMyWorkPanel 真实源码闭环（需传入本机检出目录）
npm run acceptance:ohmyworkpanel -- --repository D:\AI\LinlisWorkPanel --output summary

# 初始化本地 SQLite/CAS（默认写入 .workpanel/，已忽略）
npm run knowledge -- init

# 旧 OKF 卡片只迁为 CANDIDATE，不继承旧 verified 权限
npm run knowledge -- migrate-legacy --root knowledge

# 查询默认只返回已通过行为门禁并发布的 VERIFIED 知识
npm run knowledge -- query --q connecter

# 启用受保护的写 API 后启动 Dashboard
$env:WP_KNOWLEDGE_WRITE_TOKEN = '<local-secret>'
npm run knowledge:serve
```

Dashboard 默认监听 `http://127.0.0.1:4174`。页面默认处于只读模式；配置 `WP_KNOWLEDGE_WRITE_TOKEN` 后可以在当前页面内存中进入治理模式并提交 feedback，但自动 Run、状态转换和发布不会作为普通页面按钮暴露。没有 token 时所有 HTTP 写操作 fail closed。完整 CLI 和发布示例见 [`endlessWpKnowledgeRunner/docs/OPERATIONS.md`](endlessWpKnowledgeRunner/docs/OPERATIONS.md)。

服务器部署时可通过 `WP_KNOWLEDGE_HOST` 和 `WP_KNOWLEDGE_PORT` 覆盖监听地址，例如以只读方式运行 `WP_KNOWLEDGE_HOST=0.0.0.0 WP_KNOWLEDGE_PORT=80 npm run knowledge:serve`。公网写操作应放在 TLS 反向代理之后，并在云安全组中限制来源地址。
