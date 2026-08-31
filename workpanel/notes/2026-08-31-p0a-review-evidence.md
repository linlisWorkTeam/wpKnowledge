# P0-A MR 评审证据与复现记录

## 元数据

- 日期：2026-08-31
- 研究对象：[wpKnowledge PR #11](https://github.com/linlisWorkTeam/wpKnowledge/pull/11)
- 基线 commit：`6999099f2d7ffb1f37aca743674f325072fe39fd`
- PR head：`aa7592a67ba913de717d419ea66efa8d43a3fafc`
- 本笔记只保存复现事实、命令和未确认项；分析结论见 `../docs/2026-08-31-p0a-knowledge-flywheel-feasibility-review.md`。

## PR 状态快照

- 状态：OPEN
- 是否合入：否
- merge state：CLEAN
- 变更：38 个新增文件，约 `+1367/-0`
- 检查、Review、Comment：快照时均为空

## 规范验证

在 PR 检出目录运行新 validator，结果：

```text
SPEC_VALIDATION_OK schemas=7 commands=7 results=8 p0=25
```

验证范围：JSON Schema/meta-schema、命令与结果引用、角色 fixture、Markdown 链接、P0 追踪矩阵。它没有启动 LangGraph、DSH、CAS 或 C++ sandbox。

## 现有 Python MVP 测试

隔离环境：Python 3.13 virtualenv，仅安装 pytest。命令：

```text
python -m pytest tests -q
```

结果：

```text
68 passed, 19 failed
```

19 个失败都落在需要编译/运行 C 或 C++ 的测试路径，错误包含：

```text
compiler unavailable: [WinError 2]
```

主机检查没有发现 `gcc`、`g++`、`clang`、`clang++` 或 `cl`。因此这些测试的状态应解释为“工具链缺失导致不可复现”，不能解释为已证明的实现缺陷。

系统 Python 3.8 在测试收集阶段因 `Path | None` 失败；Python 3.13 可完成收集和非编译测试。待确认并显式约束最低 Python 版本（按语法至少 3.10）。

## 冲突证据

- 新 `specs/README.md`：声称 `specs/` 是 Accepted P0-A 的单一事实源，并要求需求 ID 永不复用。
- 现有 `mvp-flywheel/docs/README.md`：声称当前 SDD 文档是实现和验收的规范依据。
- 新旧两处均定义 `SYS-001` 等编号，但含义不同。
- 现有需求把“从已有知识开始”作为 P0 主路径；新流程默认从参考快照进入 DocGen/TestGen。

## DSH 源码快照

路径：`D:\AI\deepseek-harness\deepseek-harness`

commit：`b150a551b8d465e31e418e1b2eaf5e79bbb7d28e`

确认能力：

- `packages/bundle/headless/README.md`：一次性任务、持久化 Agent Session、完成后输出最终结果，无 HTTP 服务。
- `packages/subagent/subagent-dsh-sdk/README.md`：每次任务启动新的完整 DSH 子进程，通过 stdio JSON-RPC 驱动，具有自己的 composition、session、model route 和 tools。
- `examples/headless-agent/README.md`：本地文件/命令、subagent、workflow、JSONL persistence；含 E2B provider-composition PoC。

确认限制：

- 子进程 Provider 不支持由父进程强制 `outputSchema`、depth、tool filter 或 persona。
- 每个任务启动完整 runtime，没有进程池。
- SDK 子 Agent 只支持本地 cwd；远程 runtime 需要其他 backend。
- E2B 是组合 PoC，不上传/挂载宿主工作区，也不是完整 Harness 迁移。
- 官方 README 将项目标为 developer preview，并警告会有兼容性破坏。

## `endlessWpKnowledgeRunner` 当前验证

在基线 commit `6999099f2d7ffb1f37aca743674f325072fe39fd` 的隔离检出目录执行：

```text
python -m unittest discover -s tests -v
```

结果为 18 项通过、0 项失败，覆盖 ingest gate、劣化版本保护、history、liveMode scan、OKF roundtrip、BM25、反馈、评分信号、路径名安全和 provenance 约束。

源码与文档确认的边界：

- 当前门禁验证知识卡文档质量，不执行“知识 → 代码 → 行为等价”强评测；
- 文件写入没有事务和锁；
- DSH 插件通过 shell 调 Python CLI，动态插件依赖 DSH 进程生命周期；
- Dashboard 直接加载 runner 模块，并暴露会修改 feedback/rescore 状态的接口；
- 仓库跟踪了 `__pycache__/*.pyc` 生成文件；
- 设计文档仍写“15 项测试”，与当前实际 18 项存在文档漂移。

## 未确认事项

1. 真实 GLM/DeepSeek 模型在固定 fixture 上的成功率、波动和成本。
2. LangGraph SQLite checkpointer 与业务数据库事务之间的断电窗口。
3. Windows/AppContainer、Hyper-V container、E2B 三种隔离方案在 C++ 工具链下的性能和运维成本。
4. `endlessWpKnowledgeRunner/` 与新 AgentProvider 的可复用边界。
5. reference bug 的人工审批、测试升级和知识版本策略。
