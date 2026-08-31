# ohMyWorkPanel 固定 commit 真实源码闭环验收

## 元数据

- 日期：2026-09-01（Asia/Hong_Kong）
- 研究对象：`linlisWorkTeam/ohMyWorkPanel` 的 mention 匹配顺序实现
- 本地只读检出：`D:\AI\LinlisWorkPanel`
- 最终复验时 checkout HEAD：`b1af2659aea5068643729ee995bb944bf27b7a37`（`codex/self-marketing-mvp`，与被验收 commit 分开记录）
- 固定 commit：`cfef082d7a9e5d434777374bd6b99ef8cd309cfc`
- 场景：`acceptance/ohmyworkpanel/scenario.json`
- 验收需求：`KF-SYS-017`、`NFR-011`、`AC-E2E-001`

## 研究对象与证据来源

源码快照由 `TrustedProjectEvaluator` 使用 `git archive` 从固定 commit 解出到一次性临时目录。输入包含 `src/mentions.ts`、对应测试、公开类型、`package.json` 与锁文件；生成器唯一允许覆盖的路径是 `src/mentions.ts`。最终复验时当前分支已前进到另一个 HEAD 且有另一 Agent 的未提交文档/源码改动，评测器仍从对象库只读归档锁定 commit，没有 checkout、覆盖或复制结果回源码目录；报告在验收前后观察到 checkout HEAD 均为 `b1af265...`、dirty 状态均为 `true`。

Agent 侧使用仓库内 `SchemaValidatedScenarioAgent` 重放五个固定响应，并分别按 DocGen、CodeGen、Review 的 JSON Schema 校验。执行侧不采信 Agent 自报分数，而是在隔离于源码检出的临时工作区实际运行参考实现和两版生成实现。

## 复现命令

```powershell
npm run acceptance:ohmyworkpanel -- `
  --repository D:\AI\LinlisWorkPanel `
  --runtime D:\AI\wpKnowledge-pr11\.workpanel\ohmy-e2e-evidence `
  --output summary
```

依赖准备在快照中执行 `pnpm install --frozen-lockfile --prefer-offline`。参考门执行定向 Vitest；首版门执行同一测试并要求失败；最终门依次执行五次定向 Vitest、完整前端测试、生产构建和 Rust library 测试。

## 工具链

| 工具 | 记录版本 |
|---|---|
| 平台 | `win32-x64` |
| Node.js | `v24.11.1` |
| Git | `2.47.1.windows.2` |
| tar | `bsdtar 3.5.2` |
| pnpm | `11.7.0` |
| cargo | `1.94.1` |
| rustc | `1.94.1` |

参考门和首版门的工具链指纹为 `sha256:9d791713b1e2d9a1a691358562f394a9bbb2f621221dcf69dfbd076b2ce9e45b`；最终门增加 Rust 工具链后为 `sha256:8cf535d89d4aec3398e969b28ef39ab82208774d578302cd6148f8f38a2bdaef`。

## 闭环结果

最终 fresh 复验运行 ID：`31520d49-3a92-4fc7-9bcb-44eee7bb0028`。

| 阶段 | 结果 | 测试 | 门禁 |
|---|---:|---:|---|
| 固定 commit 参考实现 | 通过 | 1/1 | reference gate 通过 |
| 第一版生成实现 | 失败 | 0/1 | `ITERATE` |
| Correction 后全新生成 | 通过 | 279/279 | `PASS` |

首版故意把 mention display name 按较短名称优先排序，复现了前缀重叠名称会先命中错误成员的问题。Review 产出 `COR-OHMY-MENTION-ORDER-001`，把 `匹配规则` 的验收标准收紧为“前缀重叠 display name 必须按长度降序”。应用层逐字确认 DocGen 只修改该 Markdown 二级章节；第二次 CodeGen 不读取首版实现并从修订知识重新生成，最终完成：

- 定向 Vitest 连续 5 次通过；
- 完整前端测试 123 项通过；
- 生产构建通过；
- Rust library 测试 150 项通过；
- 合计 279/279，稳定度 1；
- 最终知识版本 `kv_08b9f7eec15a280cf70f3bf4` 为 `VERIFIED`；
- Gate decision `bbb17235-957c-46ff-a101-d9bc29b7096c`；
- publication key `ohmyworkpanel-mentions:kv_08b9f7eec15a280cf70f3bf4:local-v1`；
- 重复发布返回同一 receipt，证明幂等重放。

## 不可变证据索引

所有工件均存于本次运行的本地 CAS；以下 ID 可对内容重新计算 SHA-256 校验。`.workpanel/` 是忽略目录，数据库和工件不提交 Git，本笔记提交可审计索引。

| 工件 | Artifact ID |
|---|---|
| 场景定义（含命令配置） | `sha256:f95968d6f21cc498ced0112a6a550fc3b9e3e12976531c37b361b754b66989ed` |
| 源码 manifest | `sha256:14ff2f68e052f19bad6edf870063dda90f3398d9d461cf909a326a2144e42395` |
| 参考实现执行证据 | `sha256:4e1f2d56ea554ceefa5060130668d04261524afe4392820d7d3e5384141434ea` |
| 首版失败执行证据 | `sha256:89dc30b13f6d272f40c2df6a800d536d49408e007204a6a87da3b486fe315539` |
| 修订前知识正文 | `sha256:0ccb7fb3067f469d5bd199bbb93de3aea1dc1c6ad03215f91f4098a88a330bdf` |
| 修订后知识正文 | `sha256:42a3e0f51c01f7b2084ba9be650c81a90ab47694aa2973d13e3559604ed10101` |
| 最终 279/279 执行证据 | `sha256:96a0ea4eb9a265b2299173432adb0d0b3325729315642f4c98385f11b2c7e45d` |
| 完整闭环报告 | `sha256:3a181a093cb6ae768f8b34acd015eaed9da19535b9aca14a7c7964ed77a029eb` |

最终报告记录了源码路径、remote、commit、dirty 状态、生成文件摘要、准备与门禁命令的 argv、执行次数、退出码、超时/输出上限状态、经过路径与凭据脱敏的 stdout/stderr、测试计数、工具链版本、知识版本谱系、Correction、门禁、发布 receipt 和有序事件序列。

## 结论与建议

`endlessWpKnowledgeRunner` 的兼容入口与新 TypeScript 核心现在可以共用同一 Registry/CAS；真实源码薄切片证明新核心能够把一次执行失败转化为可追踪 Correction、增量知识修订、fresh 代码再生成、独立执行门禁和原子发布。建议把该命令保留为 PR/发布前的人工重验门，并在 ohMyWorkPanel 固定 commit 或工具链升级时显式更新场景和证据笔记。

## 证据边界

- Agent Provider 是确定性、Schema 校验的场景重放，只证明契约与编排，不证明真实 GLM/DeepSeek 的质量、波动、成本或权限隔离。
- `TrustedProjectEvaluator` 通过临时工作区、工具白名单、无 shell 启动、环境清理、超时、输出上限和进程树终止降低误操作风险，但它不是敌对代码沙箱；本结果不得外推为不可信 C++ 安全证明。
- 依赖安装严格使用仓库锁文件并优先离线缓存，但仍依赖当时机器已有或可解析的包源与 Rust 工具链。
- 279 项是各门禁执行结果的聚合，其中生产构建按一次成功门计数；它不是 279 个互不重叠的测试用例。
- CAS 证据位于本机忽略目录。本笔记固定其哈希与关键字段，其他机器复验会产生新的 run ID、时间戳和报告哈希。
- 最终复验开始前，ohMyWorkPanel 已存在另一 Agent 正在写入的用户改动；验收前后 checkout HEAD/dirty 摘要稳定，这些改动未被读取、覆盖或纳入固定 commit 快照，也不属于本验收产物。
