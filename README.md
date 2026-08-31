# wpKnowledge

知识飞轮平台、可验证知识注册表与研究知识库。

## 仓库边界

- `packages/domain/`：纯领域模型、状态转换、ArtifactRef 和确定性 Gate。
- `packages/contracts/`：Artifact、Agent、Sandbox、LanguagePlugin 和 Registry 端口。
- `packages/application/`：候选知识、质量门禁、行为评测、发布、检查点与检索应用服务。
- `packages/adapters/`：SQLite/CAS、旧 OKF 数据迁移和 DSH HTTP 适配器。
- `apps/runner/`：CLI、受保护的 HTTP API 和只读 Dashboard。
- `knowledge/`：研究资料和旧 OKF 卡片的 Git 可评审来源；不再充当运行时状态数据库。
- `specs/`：需求、架构、Agent、工作流、Schema、ADR 和验收规范。

目录职责、来源编号、分类和插入规则见 [`knowledge/知识库目录.md`](knowledge/知识库目录.md)。新运行时架构见 [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)，旧系统迁移见 [`docs/MIGRATION.md`](docs/MIGRATION.md)。

## 信任语义

候选知识先经过确定性文档质量门禁，但质量合格不会自动成为 `VERIFIED`。只有独立评测器提交的 `EvaluationReport` 绑定完整性可校验的执行证据，并通过确定性 Publication Gate 后，系统才能用幂等 publication key 发布知识。仓库现已提供固定 commit 的受信项目 EvalRunner：它在临时 `git archive` 工作区执行白名单工具并记录命令、版本、退出码和截断输出；它不是敌对代码沙箱，不能外推为不可信 C++ 的生产隔离证明。

旧 `endlessWpKnowledgeRunner` 的 Python 实现已被移除，其目录保留为 Node 兼容门面：`fw.mjs` 只把仍受支持的 init、ingest、query、get、status、scan 和 feedback 命令委派给同一个 TypeScript CLI、SQLite Registry 与 CAS。旧目录状态机、自制 YAML 解析器、Python shell 桥接、动态 DSH 插件和“文档分数即 verified”语义不再存在；score、eval 和 harvest 会明确拒绝，避免形成第二套事实源。

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

Dashboard 默认监听 `http://127.0.0.1:4174`。GET API 和页面只读；没有 `WP_KNOWLEDGE_WRITE_TOKEN` 时所有 HTTP 写操作 fail closed。完整 CLI 和发布示例见 [`docs/OPERATIONS.md`](docs/OPERATIONS.md)。
