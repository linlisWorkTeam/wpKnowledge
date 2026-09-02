# domain-knowledge infrastructure

This directory contains the embedded LangGraph execution layer used by the Knowledge Flywheel. It is intentionally kept separate from `packages/domain` and `packages/application` so the graph runtime, AgentRunner providers, workspace policy and checkpoint implementation can evolve without making LangGraph a knowledge-governance dependency.

Ownership is strict:

- this module owns graph topology, parallel execution, loops, execution routing and graph checkpoints;
- wpKnowledge owns FlywheelRun, KnowledgeVersion, evaluation evidence, publication decisions and public APIs;
- graph node status is emitted through `WorkflowObserver`; the Console never reads the LangGraph SQLite schema directly;
- Agent definitions are fixed in code. The only UI-customizable value is `promptAddon`.

The code is derived from the `domain-knowledge` LangGraph spike and adapted to the wpKnowledge ports. Do not add a second knowledge store, publication registry or HTTP server here.
