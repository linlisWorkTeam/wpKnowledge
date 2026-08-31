# JSON Schema

首版 Schema 使用 JSON Schema Draft 2020-12。文件名稳定，`$id` 使用 `https://wpknowledge.local/schemas/.../v1`；破坏性修改新建 v2，不原地改变 v1 语义。

| Schema | 用途 |
|---|---|
| `artifact-ref.schema.json` | 不可变 Artifact 引用 |
| `agent-command.schema.json` | 全部 Agent 输入信封与角色 payload |
| `agent-result.schema.json` | 全部 Agent 输出信封 |
| `correction.schema.json` | Review → DocGen 修订指令 |
| `evaluation-report.schema.json` | 确定性评测报告 |
| `event.schema.json` | 领域事件信封 |
| `language-plugin.schema.json` | 插件能力、请求和标准化结果 |

