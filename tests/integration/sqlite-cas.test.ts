import assert from 'node:assert/strict';
import { existsSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import test from 'node:test';
import { acceptedCandidate, createTestComposition } from '../helpers/fixture.ts';

test('CAS deduplicates immutable content and detects corruption', async () => {
  const fixture = createTestComposition();
  try {
    const first = await fixture.artifacts.put(Buffer.from('immutable'), 'text/plain');
    const second = await fixture.artifacts.put(Buffer.from('immutable'), 'text/plain');
    assert.deepEqual(first, second);
    const path = join(fixture.runtimeDir, 'cas', 'sha256', first.sha256.slice(0, 2), first.sha256);
    assert.equal(existsSync(path), true);
    writeFileSync(path, 'corrupt');
    assert.equal(await fixture.artifacts.verify(first), false);
  } finally {
    fixture.dispose();
  }
});

test('candidate ingestion is idempotent and never self-publishes', async () => {
  const fixture = createTestComposition();
  try {
    const first = await acceptedCandidate(fixture);
    const second = await acceptedCandidate(fixture);
    assert.equal(first.quality.outcome, 'ACCEPTED');
    assert.equal(first.version.status, 'CANDIDATE');
    assert.equal(first.version.gateDecisionId, null);
    assert.equal(second.replayed, true);
    assert.equal(second.version.versionId, first.version.versionId);
    assert.equal(fixture.service.status().verified, 0);
  } finally {
    fixture.dispose();
  }
});

test('candidate ingestion rejects malformed provenance at the application boundary', async () => {
  const fixture = createTestComposition();
  try {
    await assert.rejects(
      fixture.service.ingestCandidate({
        moduleId: 'invalid-provenance',
        body: '## Why\nA sufficiently explicit body.\n\n## Verification\n`npm test`',
        provenance: [null] as never[],
      }),
      /provenance entry must be an object/,
    );
  } finally {
    fixture.dispose();
  }
});

test('checkpoint returns committed output without repeating operation', async () => {
  const fixture = createTestComposition();
  try {
    const run = fixture.service.createRun('knowledge-gate', 'local-v1');
    let executions = 0;
    const execute = () => fixture.service.executeNode({
      runId: run.runId, nodeId: 'docgen', generationKey: `${run.runId}:docgen:0`, inputRefs: [],
    }, async () => {
      executions += 1;
      return [await fixture.artifacts.put(Buffer.from('node output'), 'text/plain')];
    });
    const first = await execute();
    const second = await execute();
    assert.equal(first.status, 'COMMITTED');
    assert.deepEqual(second.outputRefs, first.outputRefs);
    assert.equal(executions, 1);
  } finally {
    fixture.dispose();
  }
});

test('checkpoint fails closed under concurrent duplicate execution', async () => {
  const fixture = createTestComposition();
  try {
    const run = fixture.service.createRun('knowledge-gate', 'local-v1');
    const input = {
      runId: run.runId, nodeId: 'docgen', generationKey: `${run.runId}:docgen:0`, inputRefs: [],
    };
    let releaseOperation!: () => void;
    let markStarted!: () => void;
    const blocked = new Promise<void>((resolve) => { releaseOperation = resolve; });
    const started = new Promise<void>((resolve) => { markStarted = resolve; });
    let executions = 0;
    const first = fixture.service.executeNode(input, async () => {
      executions += 1;
      markStarted();
      await blocked;
      return [await fixture.artifacts.put(Buffer.from('node output'), 'text/plain')];
    });
    await started;
    await assert.rejects(
      fixture.service.executeNode(input, async () => {
        executions += 1;
        return [];
      }),
      /checkpoint is already running/,
    );
    releaseOperation();
    assert.equal((await first).status, 'COMMITTED');
    assert.equal(executions, 1);
  } finally {
    fixture.dispose();
  }
});

test('failed checkpoint is recorded and can be retried once', async () => {
  const fixture = createTestComposition();
  try {
    const run = fixture.service.createRun('knowledge-gate', 'local-v1');
    const input = {
      runId: run.runId, nodeId: 'docgen', generationKey: `${run.runId}:docgen:0`, inputRefs: [],
    };
    await assert.rejects(
      fixture.service.executeNode(input, async () => { throw new Error('provider unavailable'); }),
      /provider unavailable/,
    );
    assert.equal(fixture.repository.getCheckpoint(input.generationKey)?.status, 'FAILED');
    const retried = await fixture.service.executeNode(input, async () => [
      await fixture.artifacts.put(Buffer.from('recovered output'), 'text/plain'),
    ]);
    assert.equal(retried.status, 'COMMITTED');
    assert.equal(retried.retryCount, 1);
    assert.deepEqual(fixture.repository.listEvents(run.runId).map((event) => event.eventType), [
      'RunCreated', 'NodeFailed', 'NodeCompleted',
    ]);
  } finally {
    fixture.dispose();
  }
});

test('event audit order follows commit sequence when timestamps collide', async () => {
  const fixture = createTestComposition(() => '2026-08-31T00:00:00.000Z');
  try {
    const run = fixture.service.createRun('audit-order', 'local-v1');
    fixture.service.transition(run.runId, 'PLANNED');
    fixture.service.transition(run.runId, 'GENERATING');
    assert.deepEqual(fixture.repository.listEvents(run.runId).map((event) => event.eventType), [
      'RunCreated', 'RunStateChanged', 'RunStateChanged',
    ]);
  } finally {
    fixture.dispose();
  }
});

test('evaluation, decision, review transition, and events roll back atomically', async () => {
  const fixture = createTestComposition(() => '2026-08-31T00:00:00.000Z');
  try {
    const candidate = await acceptedCandidate(fixture, '-atomic-evaluation');
    let run = fixture.service.createRun(candidate.version.moduleId, 'local-v1');
    run = fixture.service.transition(run.runId, 'PLANNED');
    run = fixture.service.transition(run.runId, 'GENERATING');
    run = fixture.service.transition(run.runId, 'EVALUATING');
    const report = {
      reportId: 'report-rollback', runId: run.runId, versionId: candidate.version.versionId,
      inputRefs: [candidate.version.bodyRef], evidenceRefs: [candidate.version.bodyRef],
      toolchainFingerprint: 'fixture@1', criticalFailures: 0, testsPassed: 1, testsTotal: 1,
      stability: 1, infrastructureFailure: false, createdAt: run.updatedAt,
    };
    const decision = {
      decisionId: 'decision-rollback', runId: run.runId, versionId: candidate.version.versionId,
      outcome: 'PASS' as const, reasonCodes: ['ALL_DETERMINISTIC_GATES_PASSED'],
      evidenceRefs: [candidate.version.bodyRef], createdAt: run.updatedAt,
    };
    const event = (eventId: string, eventType: string) => ({
      eventId, eventType, schemaVersion: '1.0' as const, runId: run.runId,
      occurredAt: run.updatedAt, causationId: null, payload: {},
    });
    const eventsBefore = fixture.repository.listEvents(run.runId);
    assert.throws(() => fixture.repository.saveEvaluationAndDecision(
      report, decision, { ...run, runId: 'missing-run', state: 'REVIEWING' },
      event('gate-rollback', 'GateDecided'), event('transition-rollback', 'RunStateChanged'),
    ), /run is not EVALUATING/);
    assert.equal(fixture.repository.getGateDecision(decision.decisionId), null);
    assert.equal(fixture.repository.getRun(run.runId)?.state, 'EVALUATING');
    assert.deepEqual(fixture.repository.listEvents(run.runId), eventsBefore);
  } finally {
    fixture.dispose();
  }
});
