import assert from 'node:assert/strict';
import test from 'node:test';
import {
  artifactIdFor, createArtifactRef, createRun, decideGate, transitionRun,
} from '../../packages/domain/src/index.ts';

test('artifact ID is bound to content digest', () => {
  const ref = createArtifactRef(Buffer.from('hello'), 'text/plain');
  assert.equal(ref.artifactId, artifactIdFor(ref.sha256));
  assert.equal(ref.size, 5);
});

test('run transitions are monotonic and reject illegal jumps', () => {
  const created = createRun('module-a', 'policy-a', '2026-08-31T00:00:00.000Z');
  const planned = transitionRun(created, 'PLANNED', '2026-08-31T00:00:01.000Z');
  const generating = transitionRun(planned, 'GENERATING', '2026-08-31T00:00:02.000Z');
  const evaluating = transitionRun(generating, 'EVALUATING', '2026-08-31T00:00:03.000Z');
  assert.equal(evaluating.iteration, 0);
  assert.throws(() => transitionRun(evaluating, 'VERIFIED', '2026-08-31T00:00:04.000Z'), /illegal run transition/);
});

test('deterministic gate passes only complete and stable evidence', () => {
  let run = createRun('module-a', 'policy-a', '2026-08-31T00:00:00.000Z');
  run = transitionRun(run, 'PLANNED', '2026-08-31T00:00:01.000Z');
  run = transitionRun(run, 'GENERATING', '2026-08-31T00:00:02.000Z');
  run = transitionRun(run, 'EVALUATING', '2026-08-31T00:00:03.000Z');
  const decision = decideGate(run, {
    reportId: 'report', runId: run.runId, versionId: 'version', inputRefs: [], evidenceRefs: [],
    toolchainFingerprint: 'fake@1', criticalFailures: 0, testsPassed: 10, testsTotal: 10,
    stability: 1, infrastructureFailure: false, createdAt: '2026-08-31T00:00:04.000Z',
  }, { policyId: 'policy-a', minimumStability: 1, requireAllTests: true, maxIterations: 3 }, '2026-08-31T00:00:05.000Z');
  assert.equal(decision.outcome, 'PASS');
  assert.deepEqual(decision.reasonCodes, ['ALL_DETERMINISTIC_GATES_PASSED']);
});

test('deterministic gate iterates on behavioral failure', () => {
  let run = createRun('module-a', 'policy-a', '2026-08-31T00:00:00.000Z');
  run = transitionRun(run, 'PLANNED', '2026-08-31T00:00:01.000Z');
  run = transitionRun(run, 'GENERATING', '2026-08-31T00:00:02.000Z');
  run = transitionRun(run, 'EVALUATING', '2026-08-31T00:00:03.000Z');
  const decision = decideGate(run, {
    reportId: 'report', runId: run.runId, versionId: 'version', inputRefs: [], evidenceRefs: [],
    toolchainFingerprint: 'fake@1', criticalFailures: 1, testsPassed: 9, testsTotal: 10,
    stability: 0.8, infrastructureFailure: false, createdAt: '2026-08-31T00:00:04.000Z',
  }, { policyId: 'policy-a', minimumStability: 1, requireAllTests: true, maxIterations: 3 }, '2026-08-31T00:00:05.000Z');
  assert.equal(decision.outcome, 'ITERATE');
  assert.ok(decision.reasonCodes.includes('CRITICAL_TEST_FAILURE'));
});

test('infrastructure failure remains STOPPED when behavioral checks also fail', () => {
  const run = createRun('module-a', 'policy-a', '2026-08-31T00:00:00.000Z');
  const decision = decideGate(run, {
    reportId: 'report', runId: run.runId, versionId: 'version', inputRefs: [], evidenceRefs: [],
    toolchainFingerprint: 'fake@1', criticalFailures: 1, testsPassed: 0, testsTotal: 1,
    stability: 0, infrastructureFailure: true, createdAt: '2026-08-31T00:00:01.000Z',
  }, { policyId: 'policy-a', minimumStability: 1, requireAllTests: true, maxIterations: 3 }, '2026-08-31T00:00:02.000Z');
  assert.equal(decision.outcome, 'STOPPED');
  assert.ok(decision.reasonCodes.includes('INFRASTRUCTURE_FAILURE'));
});
