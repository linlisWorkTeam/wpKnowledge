import assert from 'node:assert/strict';
import test from 'node:test';
import { createDomainKnowledgeInfrastructure } from '../../infrastructure/domain-knowledge/src/index.ts';
import type {
  AgentId, WorkflowNodeProjection, WorkflowStageInput,
} from '../../packages/contracts/src/index.ts';

test('embedded LangGraph runs every fixed Agent and exposes node projections', async () => {
  const calls: WorkflowStageInput[] = [];
  const projections: WorkflowNodeProjection[] = [];
  const infrastructure = await createDomainKnowledgeInfrastructure({
    checkpoint: { kind: 'memory' },
    prompts: { getPromptAddon: (agentId) => agentId === 'doc-gen' ? 'Explain the boundary first.' : '' },
    observer: { record: (projection) => projections.push(structuredClone(projection)) },
    executor: {
      async execute(input) {
        calls.push(structuredClone({ ...input, signal: undefined }));
        if (input.nodeId === 'workflow_router') {
          return {
            detail: input.iteration === 1 ? 'iterate once' : 'ready',
            route: input.iteration === 1 ? 'ITERATE' : 'PASS',
          };
        }
        return { detail: `${input.nodeId} complete`, context: { [`seen:${input.nodeId}:${input.iteration}`]: true } };
      },
    },
  });
  const handle = await infrastructure.engine.start({
    runId: 'embedded-graph', maxIterations: 3, workerCount: 2,
  });
  const result = await infrastructure.engine.wait(handle.runId);

  assert.equal(result.executionStatus, 'COMPLETED');
  assert.equal(result.route, 'PASS');
  assert.equal(result.iteration, 2);
  const calledAgents = new Set(calls.map((call) => call.agentId).filter(Boolean));
  assert.deepEqual([...calledAgents].sort(), [
    'check', 'code', 'doc-gen', 'doc-worker', 'orchestrator', 'review', 'test-gen',
  ] satisfies AgentId[]);
  assert.match(calls.find((call) => call.agentId === 'doc-gen')?.prompt ?? '', /Explain the boundary first/);
  assert.ok(projections.some((projection) => projection.nodeId === 'doc_worker:worker-1'));
  assert.ok(projections.some((projection) => projection.nodeId === 'publication' && projection.status === 'COMPLETED'));
  assert.ok(projections.every((projection) => projection.runId === handle.runId));
});

test('embedded LangGraph cancellation wins over an aborted node invocation', async () => {
  let enteredNode!: () => void;
  const entered = new Promise<void>((resolve) => { enteredNode = resolve; });
  const infrastructure = await createDomainKnowledgeInfrastructure({
    checkpoint: { kind: 'memory' },
    prompts: { getPromptAddon: () => '' },
    observer: { record: () => undefined },
    executor: {
      async execute(input) {
        enteredNode();
        await new Promise<void>((_resolve, reject) => {
          input.signal?.addEventListener('abort', () => reject(new Error('cancelled by operator')), { once: true });
        });
        return { detail: 'unreachable' };
      },
    },
  });
  const handle = await infrastructure.engine.start({
    runId: 'cancelled-graph', maxIterations: 2, workerCount: 1,
  });
  await entered;
  await infrastructure.engine.cancel(handle.runId);

  assert.equal((await infrastructure.engine.status(handle.runId)).executionStatus, 'CANCELLED');
});
