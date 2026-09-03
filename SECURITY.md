# 安全策略

<details lang="en">
<summary>English summary</summary>

Do not publish secrets, credentials, personal data or exploitable details in this content repository. Report vulnerabilities privately through GitHub Security. Runtime security issues belong to domain-knowledge; knowledge and evidence must be redacted before review.

</details>

## 本仓库的安全范围

wpKnowledge 保存知识与证据，不运行 Agent、API 或评测任务。Knowledge Flywheel 的执行安全、鉴权、隔离和依赖漏洞由 [domain-knowledge](https://github.com/linlisWorkTeam/domain-knowledge) 负责。

本仓主要关注两类风险：

- 文档、截图或日志泄露密钥、令牌、个人信息、内部地址和外部登录态；
- 公开材料包含尚未修复、可直接利用的漏洞细节。

## 报告问题

请优先使用仓库 Security 页面提供的私密漏洞报告入口。不要在公开 Issue、PR、讨论区或知识文档中提交凭据、完整复现或可直接利用的代码。若私密入口尚未启用，只创建不含细节的公开 Issue，请维护者提供私密联系方式。

报告中可包含受影响仓库与 commit、问题范围、最小复现条件、潜在影响和临时缓解方式。若问题属于运行时，请同时指出对应的 `domain-knowledge` 路径或版本。

## 提交证据前

- 用占位符替换 API key、Token、Cookie 和账号信息；
- 删除与结论无关的用户数据、绝对路径和完整环境变量；
- 截图裁掉浏览器会话、终端凭据和个人信息；
- 只保留验证结论所需的最小日志片段；
- 不提交 SQLite、CAS、Checkpoint、`.workpanel/` 或模型供应商登录态。

曾经暴露过的凭据不能靠删除文件恢复安全，应立即吊销并轮换。
