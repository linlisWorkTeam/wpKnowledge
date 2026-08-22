# endlessWpKnowledgeRunner 飞轮分析证据

日期：2026-08-22

## 基线

- 仓库：`D:\AI\wpKnowledge`
- 目标目录：`endlessWpKnowledgeRunner/`
- commit：`c8f1d8d25b39edfeea0c9aa712f8b541159a6872`
- 分支：`main`，本地领先 `origin/main` 8 个提交
- 当前未提交：运行产生的 tracked `__pycache__/*.pyc`，未清理

## 验证命令与结果

```text
cd D:\AI\wpKnowledge\endlessWpKnowledgeRunner
python -m unittest discover -s tests -v
```

结果：15 个测试全部通过。

```text
python fw.py status --json
```

结果：`concepts_total=4`、`verified=3`、`drafts=1`、`avg_score=76.3`、`feedback_events=5`。

```text
python fw.py query --q connecter --top 5 --no-feedback --json
```

结果：3 个 verified 命中，`workpanel-connecter` 第一名，保存分 93.0。

```text
python fw.py eval --name workpanel-connecter --runs 5 --json
```

结果：mean 95.8、std 0、min/max 95.8、5 次 gate 均 pass；实时分高于卡片保存分，说明 usage 变化后没有自动持久化 rescore。

## 隔离行为验证

在临时目录创建独立 Store，未修改仓库知识卡：

- `util.tokenize("alpha alpha alpha")` 输出 `['alpha']`；
- 使用 Unicode escape 启动三个独立 Python 进程，`slugify("知识")` 产生不同的 `zNNNNNN`，证明内置 `hash()` 造成跨进程不稳定；
- `force_draft` 生成的 draft 得到 `score_command=pass` 时，Store 中 status 仍为 `draft`，证明 `score_one` 不负责状态迁移。

## 关键源码证据

- CLI 编排：`endlessWpKnowledgeRunner/fw.py:49-193`
- ingest 与 verified 防污染：`endlessWpKnowledgeRunner/fwrunner/ingest.py:54-225`
- 文件 Bundle 与 ledger：`endlessWpKnowledgeRunner/fwrunner/store.py:49-71,118-189,224-277`
- 评分器：`endlessWpKnowledgeRunner/fwrunner/scorer.py:54-303`
- 检索与命中反馈：`endlessWpKnowledgeRunner/fwrunner/retrieve.py:27-136`
- liveMode 扫描：`endlessWpKnowledgeRunner/fwrunner/livemode.py:21-78`
- DSH shell、harvester、timer、HTTP：`endlessWpKnowledgeRunner/dsh/fw-plugin.js:33-162,339-455`
- 测试覆盖：`endlessWpKnowledgeRunner/tests/test_fwrunner.py:64-205`

## 未验证事项

- 两个并发 writer 同时更新 ledger/card/index 时的损坏与覆盖行为；
- 真实 DSH Cordis 宿主内的插件加载、subagent structured output 和 timer 生命周期；
- `/flywheel/*` HTTP 端点的鉴权、限流和恶意参数行为；
- source URL/commit 的联网真实性校验；
- jury JSON 的生产生成链路及其对 gate 的实际影响；
- 多进程或多机器 liveMode 的重复领取、崩溃恢复和任务幂等。
