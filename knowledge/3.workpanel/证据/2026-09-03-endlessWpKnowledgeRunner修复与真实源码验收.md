# endlessWpKnowledgeRunner 修复与真实源码验收记录

## 基本信息

- 日期：2026 年 9 月 3 日
- 仓库工作树：`D:\AI\wpKnowledge-pr26`
- 分支：`codex/ddd-layered-console-copy`
- 基线：`origin/main@90db60da26fa0479a81ae466335c8670f3eb3b43`
- 真实源码：`D:\AI\LinlisWorkPanel`
- 固定提交：`3b2e6073e01b42e2a595fca4de3acaad44715ddd`

## 自动化验证

```text
npm ci
结果：安装 577 个包，0 个已知漏洞

npm run typecheck
结果：通过

npm run validate:specs
结果：SPEC_VALIDATION_OK schemas=7 commands=7 results=8 p0=36

npm test
结果：tests 94，pass 92，fail 0，skipped 2

GitHub Actions
结果：CI verify 通过，运行号 33655089563
```

跳过项分别是只在 Linux 存在 Bubblewrap 时执行的 DSH 隔离用例，以及需要 Windows 符号链接权限的来源拒绝用例。路径穿越、旧视图残留、嵌套工作区和环境净化用例均在本机实际执行并通过。

## 真实源码闭环

执行命令：

```text
npm run acceptance:ohmyworkpanel -- \
  --repository D:\AI\LinlisWorkPanel \
  --runtime .workpanel\acceptance-final-10 \
  --output summary
```

最终结果：

```text
runId: 6eb6ed22-fe5f-45c1-b8ed-618847cf60f3
commit: 3b2e6073e01b42e2a595fca4de3acaad44715ddd
reference: 1/1
first: 0/1
firstGate: ITERATE
final: 294/294
finalGate: PASS
finalStatus: VERIFIED
report sha256: 5440a8658f99c6c1f8e17faf78106979d772ae258f54f3a121c520a6e50761aa
report size: 51913 bytes
```

最终评测包含 5 次目标模块稳定性测试、ohMyWorkPanel 全量前端测试、生产构建和 Rust 库测试。发布回执为 `ohmyworkpanel-mentions:kv_69f45675c18a583cb5a56bd9:local-v1`。

## 失败记录与处理

第一次复验的最终门禁停在继续迭代。评测证据显示前端 130/130 已通过，失败项是 Windows rustup 在临时用户目录中找不到默认工具链。修复后，受信适配器解析具体工具链可执行文件，评测子进程仍不继承真实 `HOME`、`USERPROFILE`、`APPDATA` 或语言包管理器主目录。

后续几次参考门禁失败来自 registry 连接重置和 pnpm 缓存参数位置错误。最终方案把固定锁文件安装与正式测试分开：准备阶段可以读取内容寻址包缓存，测试阶段只使用临时工作区内安装好的依赖。缓存不完整时离线安装明确失败，不会把网络抖动写成测试失败或伪造通过。

## 可追溯提交

最高和高优先级修复从 `68918e7` 开始，依次覆盖进程终止、审计隔离、规范契约、追踪矩阵、仓储发布、测试计数、环境净化、标准输入、同步异常、检查点租约、回滚说明和配置门禁。增强修复由 `519d432` 与 `39ea700` 归并。`2ebec4c` 记录真实复验发现的工具链与包缓存边界，`a1add8c` 补齐持续集成的完整 Git 历史，并让内容寻址存储的破坏性测试先显式解除只读位，不放宽生产对象的只读约束。

远端首次执行在 `39ea700` 失败，原因不是业务逻辑回归：浅克隆不包含发布标记所绑定的祖先提交；类 Unix 主机也无法直接覆写只读内容寻址对象。修复后，Actions 使用完整历史验证祖先关系，测试仅在故障注入前临时修改权限。最新 `verify` 用时 34 秒并通过。

Cursor Bugbot 已对四次请求返回响应，但账号侧均提示未启用，因而没有产生代码意见或批准结论。这是外部审查能力边界，不能写成“Cursor 审查通过”。

## 证据边界

完整运行数据库和内容寻址工件保存在忽略目录 `.workpanel/acceptance-final-10`，不提交大体积运行数据。本文保留命令、固定提交、运行号、门禁结果与报告摘要，足以定位本机证据。GitHub Actions 补充了类 Unix 环境验证，但现有证据仍不证明敌对代码执行安全；Cursor Bugbot 未启用，也没有形成第二套自动审查证据。
