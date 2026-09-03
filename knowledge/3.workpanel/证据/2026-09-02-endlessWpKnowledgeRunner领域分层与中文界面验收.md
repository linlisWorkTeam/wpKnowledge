# endlessWpKnowledgeRunner 领域分层与中文界面验收记录

## 基本信息

- 日期：2026-09-02
- 仓库：`D:\AI\wpKnowledge-pr26`
- 分支：`codex/ddd-layered-console-copy`
- 对照主分支：`origin/main@90db60da26fa0479a81ae466335c8670f3eb3b43`
- 核心改动提交：`0e19cfe`

## 执行命令与结果

### 类型与规范

```text
npm run typecheck
结果：通过

npm run validate:specs
结果：SPEC_VALIDATION_OK schemas=7 commands=7 results=8 p0=36
```

### 完整自动化测试

```text
npm test
结果：tests 74，pass 72，fail 0，skipped 2
```

跳过项：

- DSH SDK 的 Linux Bubblewrap 隔离测试，仅在对应平台执行。
- 角色工作区符号链接拒绝测试；本机 Windows 未授予创建符号链接权限。路径穿越测试已实际执行并通过。

### ohMyWorkPanel 真实源码闭环

```text
npm run acceptance:ohmyworkpanel -- \
  --repository D:\AI\LinlisWorkPanel \
  --runtime C:\Users\Windows11\AppData\Local\Temp\wpknowledge-ddd-20260902 \
  --output summary
```

结果：

```text
runId: a42f04ef-26db-482d-a9ca-98484e740718
commit: 3b2e6073e01b42e2a595fca4de3acaad44715ddd
reference: 1/1
first: 0/1
firstGate: ITERATE
final: 295/295
finalGate: PASS
finalStatus: VERIFIED
report sha256: 0e4f2aec4d70cc02387751dc0cf7bbbbf623952b40682c678f9784e69912cc07
report size: 43493 bytes
```

### 真实浏览器检查

本地控制台启动命令：

```text
npm run knowledge:serve
```

项目官网启动命令：

```text
npm run site:serve
```

检查结果：

- 控制台标题为“知识飞轮控制台”，固定英文标题只保留 `WORKPANEL · KNOWLEDGE FLYWHEEL`。
- 设置页显示 `.env.example`、`.env.local`、`WP_KNOWLEDGE_WRITE_TOKEN` 和重启说明。
- 未配置令牌时，页面明确说明服务端保持只读，治理模式按钮提示用户到设置查看配置方法。
- 项目官网的栏目、状态、架构说明、流程标签、边界提示和社交分享图均改为中文。
- 控制台浏览器日志：0 错误、0 警告。
- 项目官网浏览器日志：0 错误、0 警告。

## 结构核对

- 运行时代码已收敛到 `endlessWpKnowledgeRunner/src/{domain,application,infrastructure,interfaces}`。
- Git 跟踪文件中不存在组件内旧的 `apps/`、`packages/` 或顶层 `infrastructure/` 源码根。
- 架构契约测试禁止领域层向外依赖、应用层依赖基础设施或交互层、基础设施层依赖交互入口。
- 所有命令入口、类型检查范围、文档链接和验收导入已指向新路径。

## 证据边界

本记录是本机、当前依赖锁和固定源码提交下的验收结果。它不证明敌对代码执行安全，也不把一次模型运行外推为长期稳定性结论。运行数据库和内容寻址工件保存在临时目录，未提交到仓库。
