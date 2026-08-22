# DSH 集成说明

## 方式一：动态 Cordis 插件（当前 MVP 采用）

`fw-plugin.js` 就是 `cordis_define` 的 `code.host` 函数体（保持一致，仓库内即真源）。

再加载步骤：

1. `cordis_define`：`plugin.kind: "new"`，`idPrefix: "fwrun"`，`code.host = fw-plugin.js 内容`。
2. 对返回的 pluginId/packageId 执行 `cordis_run`（mode: run）。
3. 验证：`Tool.listTools` 应出现 `fw_ingest / fw_query / fw_get / fw_score / fw_eval / fw_status / fw_scan / fw_feedback / fw_livemode / fw_harvest`。
4. 使用：agent 可直接调用；外部系统 `GET http://127.0.0.1:3080/fw/query?q=...`。

动态插件的生命周期 = 当前 DSH 进程；进程重启后需重新加载（定义保留在会话日志，可重跑 cordis_run）。

## 方式二：Agent Preset（永久挂载）

把插件注册进某个 agent preset（`${DSH_HOME}/.agent-presets/<id>/`）的系统提示/工具层，或把插件源文件放到宿主 composition 的 Cordis 插件目录。具体做法：

```yaml
# cordis.yml（宿主组合）或 preset 的 plugins 段示例
plugins:
  - file: D:/AI/wpKnowledge/endlessWpKnowledgeRunner/dsh/fw-plugin.js   # 需为 Cordis 插件模块形态
```

> 注意：不要改部署自带组合（升级会被覆盖）；用你自己的 preset 目录。

## 权限与沙箱

- 插件通过 `shell` 服务执行 `python fw.py ...`（工作目录 = runner 根），不同宿主服务直接写文件。
- 知识库唯一写路径是 runner 自身的确定性管道（ingest/score），符合“谁评测谁不改、谁沉淀谁负责”的职责边界。
- liveMode 的 harvester 是子 agent（隔离上下文），只产出结构化提炼，不直接写 store。