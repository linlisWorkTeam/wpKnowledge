# 知识生产类 Agent

## DocGenAgent

- **职责**：从授权源码快照与 SourceRef 生成 OKF 候选知识；根据 Correction 增量修订，是知识正文唯一自动执笔者。
- **输入 Schema**：`agent-command.schema.json` 的 `docgen` payload：moduleId、sourceRefs、publicInterfaceRefs、baseKnowledgeRef/corrections（迭代时）。
- **输出 Schema**：`agent-result.schema.json` 的 `knowledgeCandidate` payload，正文为 ArtifactRef，附 provenance、变更路径和 unresolvedRisks。
- **约束**：不得复制大段源码；每项行为声明必须有 SourceRef；不能发布或修改既有版本。

## DocWorkerAgent

- **职责**：按依赖拓扑在独立上下文分析模块子集，并回传结构化片段和来源；不直接写 KnowledgeStore。
- **输入/输出**：同一统一 Schema 中 `docworker` / `knowledgeChunk` payload。
- **约束**：最多五个并行实例；只能读取分配的源码范围；跨块事实标为 dependencyRef，不猜测。

失败输出必须使用统一错误对象，并保留已知来源；上下文截断不得伪装为成功。

