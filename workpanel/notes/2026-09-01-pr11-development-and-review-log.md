# PR #11 开发、复验与审查记录

## 元数据

- 日期：2026-09-01（Asia/Hong_Kong）
- 对象：[wpKnowledge PR #11](https://github.com/linlisWorkTeam/wpKnowledge/pull/11)
- 最终 PR head：c80d1fc1de57757d9515e2045a9654f30111f9ff
- merge commit：29612b078978fba7dd1681229a6931d97185c652
- merge tree：5b512f8cf806d3889971b4424d38992bd7911fdf
- 用途：记录正式报告背后的提交、命令、审查意见、网络例外和可复验证据

## 提交时间线

| Commit | 交付内容 |
|---|---|
| 2867eec | 新增 P0-A Knowledge Flywheel specs |
| aa7592a | Schema 与 Agent contracts 对齐 |
| af7e718 | TypeScript 六边形核心替换旧 endless runner |
| ee68a24 | 归档 P0-A 可行性评审 |
| e4c59c9 | 归档 endless runner 重构评估 |
| 7f37529 | 记录实现证据和受信评测边界 |
| e1f82ee | 修复 Dashboard all-status 查询语义 |
| dc71ac7 | 固定 commit 真实源码两轮飞轮与 EvalRunner |
| fb3b5af | 修复 Cursor 第一轮 4 个问题 |
| 5c9b889 | 原子提交 Evaluation、decision 和 review transition；统一 Git 环境 |
| c80d1fc | 支持响应丢失后的评测幂等重放 |
| 29612b0 | GitHub 生成的 PR merge commit |

PR 最终统计由 GitHub API 读取：128 个文件，+7,250/−3,570 行，11 个 PR 提交。

## 关键设计与实现记录

### 1. 旧系统收敛

- 删除 Python runner 主路径、目录状态机、自制 YAML 解析器、shell DSH 桥和旧 timer harvest。
- 旧 OKF verified 迁移后只成为 CANDIDATE。
- endlessWpKnowledgeRunner/fw.mjs 只加载同一 TypeScript CLI。
- legacy get、query、ingest、scan、feedback 均有实际 facade 集成测试。
- retired command 明确失败，避免旧语义静默复活。

### 2. Evidence-bound publication

- ArtifactRef 绑定 sha256 内容摘要。
- EvaluationReport 必须有至少一个完整性可校验的 evidence artifact。
- GatePolicy 必须和 run 的 policyId 一致。
- 文档 Quality Gate 只决定是否允许行为评测。
- PASS decision 与 run/version/evidence 绑定；发布前重新核对。
- publication key 保证重复发布返回相同 receipt。

### 3. Checkpoint 和事务

- GenerationKey 对已提交节点返回原输出。
- 并发重复 claim fail closed。
- FAILED checkpoint 保留 retryCount 和事件，可受控重试。
- event_seq 确保相同时间戳下仍按提交顺序审计。
- EvaluationReport、GateDecision、REVIEWING 和事件单事务提交。
- 同输入重试返回原 decisionId；不同输入拒绝为 replay collision。

### 4. 真实源码执行

- 固定完整 commit，不接受缩写或当前 HEAD 隐式替代。
- git archive 到临时目录，不修改源码 checkout。
- 命令白名单为 node、pnpm、cargo，且 shell=false。
- 清理 GIT_DIR、GIT_WORK_TREE、credential/token 等继承环境。
- 同时保留 HOME 和 USERPROFILE，满足跨平台工具查找。
- 输出、argv 和报告做路径/凭据脱敏。
- 路径逃逸、符号链接写目标、超时、输出超限和取消均失败。

## Cursor 审查闭环

### 第一轮：dc71ac7

1. [Publish path skips required REVIEWING](https://github.com/linlisWorkTeam/wpKnowledge/pull/11#discussion_r3896590745)
   - 修复：评测完成即在同一应用语义进入 REVIEWING；发布只能 REVIEWING → PUBLISHING。
2. [Legacy get returns search hits](https://github.com/linlisWorkTeam/wpKnowledge/pull/11#discussion_r3896590763)
   - 修复：新增按 module 的精确 get，返回完整正文。
3. [Legacy query rejects no-feedback](https://github.com/linlisWorkTeam/wpKnowledge/pull/11#discussion_r3896590774)
   - 修复：安全忽略已失去副作用的旧参数。
4. [HOME environment compatibility](https://github.com/linlisWorkTeam/wpKnowledge/pull/11#discussion_r3896590789)
   - 修复：清理敏感环境时保留 Unix HOME 和 Windows USERPROFILE。

修复提交：fb3b5af。

### 第二轮：fb3b5af

1. [Evaluation save and transition split](https://github.com/linlisWorkTeam/wpKnowledge/pull/11#discussion_r3896735524)
   - 修复一：5c9b889 将 report、decision、run state 和事件放入一个 SQLite 事务。
   - 修复二：c80d1fc 为响应丢失增加精确重放，返回原 decisionId 且不重复事件。
2. [Inspect Git env is inconsistent](https://github.com/linlisWorkTeam/wpKnowledge/pull/11#discussion_r3896735530)
   - 修复：commit resolution、git show、git archive 和所有 tool probe 共用清理环境。

每条意见均在 GitHub 原 discussion 下回复了修复提交和测试证据。

### 最终检查例外

最终 head c80d1fc 触发 Cursor 后：

- Bugbot：usage limit reached，neutral；
- Approval Agent：hard limit 剩余额度不足 2 美元，neutral；
- Security Agent：hard limit 剩余额度不足 2 美元，neutral。

三者都没有输出新代码意见。这是外部账户额度限制，不记为代码通过；最终合入依据为此前实际意见全部修复、自动化门禁全绿、真实源码验收通过、GitHub mergeable=CLEAN。

## 最终复验命令

在 D:/AI/wpKnowledge-pr11 执行：

~~~powershell
npm run typecheck
npm run validate:specs
npm test
npm audit --omit=dev --audit-level=high --registry=https://registry.npmjs.org
git diff --check

npm run acceptance:ohmyworkpanel -- `
  --repository D:\AI\LinlisWorkPanel `
  --runtime D:\AI\wpKnowledge-pr11\.workpanel\ohmy-e2e-final6 `
  --output summary
~~~

结果：

- typecheck：PASS；
- Spec：SPEC_VALIDATION_OK schemas=7 commands=7 results=8 p0=28；
- tests：34/34 PASS；
- npm audit：0 vulnerabilities；
- diff check：PASS；
- ohMyWorkPanel：reference 1/1、first 0/1、final 279/279、PASS、VERIFIED。

## 最终 E2E 证据

- runId：fad0b5ff-cfb7-4943-8f97-9b552099ab93
- fixed commit：cfef082d7a9e5d434777374bd6b99ef8cd309cfc
- scenario：sha256:f95968d6f21cc498ced0112a6a550fc3b9e3e12976531c37b361b754b66989ed
- source manifest：sha256:14ff2f68e052f19bad6edf870063dda90f3398d9d461cf909a326a2144e42395
- reference evidence：sha256:0f1852f588d60cdea2295b78f0ee33f07eee06777a2976d5b6885d25c9a6bd59
- first-failure evidence：sha256:ef140a3bef85ca52651c8475bf8895641d0b14ee48db3adc7742722a64eb3e8e
- original knowledge body：sha256:0ccb7fb3067f469d5bd199bbb93de3aea1dc1c6ad03215f91f4098a88a330bdf
- revised knowledge body：sha256:42a3e0f51c01f7b2084ba9be650c81a90ab47694aa2973d13e3559604ed10101
- final evidence：sha256:43f0b4696c9486306084823cd031caeafc0c90aadd519fc368d68973a61ce109
- full report：sha256:3fd7bcca5e06afaf08c5eb02ce02d5c45968ece49aec1be0282beb0b5ebde80c

详细内容见 [ohMyWorkPanel 固定 commit 真实源码闭环验收](2026-09-01-ohmyworkpanel-real-source-e2e.md)。

## GitHub 同步与合并记录

本机到 github.com 的 Git Smart HTTP 在 fetch/push 时持续 connection reset，但 api.github.com 可用。为避免修改用户原始脏工作区和强推分叉历史，最终同步采用 GitHub Git Data API：

1. 从 PR 当时远端 tree 创建或复用 blob；
2. 创建新 tree；
3. 比较远端 tree SHA 与本地已测 commit tree；
4. 只有完全一致才创建以远端 head 为 parent 的 commit；
5. non-force 更新 PR ref；
6. 合并后再次确认 main 的 merge commit tree。

最终验证：

- 本地已测 tree：5b512f8cf806d3889971b4424d38992bd7911fdf
- 远端 PR head tree：5b512f8cf806d3889971b4424d38992bd7911fdf
- main merge commit tree：5b512f8cf806d3889971b4424d38992bd7911fdf
- main head：29612b078978fba7dd1681229a6931d97185c652

## 证据边界

- 本笔记记录的是可复验工程过程，不是独立第三方安全审计。
- Cursor 最终 head 未因额度问题获得新一轮实际分析。
- CAS 文件位于忽略目录，Artifact ID 可校验但不会随 Git 仓库分发。
- 真实 Agent、敌对代码沙箱、多机调度和完整 crash lease recovery 不属于本次已完成能力。
