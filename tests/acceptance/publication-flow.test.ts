import assert from 'node:assert/strict';
import test from 'node:test';
import { acceptedCandidate, createTestComposition } from '../helpers/fixture.ts';

test('candidate becomes VERIFIED only after integrity-checked evidence and deterministic PASS', async () => {
  const fixture = createTestComposition();
  try {
    const candidate = await acceptedCandidate(fixture);
    let run = fixture.service.createRun(candidate.version.moduleId, 'local-v1');
    run = fixture.service.transition(run.runId, 'PLANNED');
    run = fixture.service.transition(run.runId, 'GENERATING');
    run = fixture.service.transition(run.runId, 'EVALUATING');
    const evidence = await fixture.artifacts.put(Buffer.from(JSON.stringify({ tests: 12, passed: 12 })), 'application/json');
    const { decision } = await fixture.service.recordEvaluation({
      runId: run.runId,
      versionId: candidate.version.versionId,
      evidenceRefs: [evidence],
      toolchainFingerprint: 'fake-language-plugin@1.0.0',
      criticalFailures: 0,
      testsPassed: 12,
      testsTotal: 12,
      stability: 1,
    }, fixture.config.publicationGate);
    assert.equal(decision.outcome, 'PASS');
    run = fixture.service.transition(run.runId, 'REVIEWING');
    const first = await fixture.service.publish(run.runId, candidate.version.versionId, decision.decisionId);
    const replay = await fixture.service.publish(run.runId, candidate.version.versionId, decision.decisionId);
    assert.equal(first.replayed, false);
    assert.equal(replay.replayed, true);
    assert.equal(fixture.service.getKnowledgeVersion(candidate.version.versionId)?.status, 'VERIFIED');
    const query = await fixture.query.search({ query: '行为 门禁' });
    assert.equal(query.hits.length, 1);
    assert.equal(query.hits[0].status, 'VERIFIED');
    assert.equal((await fixture.query.search({ query: '行为 门禁', top: Number.NaN })).hits.length, 1);
    assert.equal(fixture.service.status().publications, 1);
  } finally {
    fixture.dispose();
  }
});

test('failed behavior gate cannot publish knowledge', async () => {
  const fixture = createTestComposition();
  try {
    const candidate = await acceptedCandidate(fixture);
    let run = fixture.service.createRun(candidate.version.moduleId, 'local-v1');
    run = fixture.service.transition(run.runId, 'PLANNED');
    run = fixture.service.transition(run.runId, 'GENERATING');
    run = fixture.service.transition(run.runId, 'EVALUATING');
    const evidence = await fixture.artifacts.put(Buffer.from('{}'), 'application/json');
    const { decision } = await fixture.service.recordEvaluation({
      runId: run.runId,
      versionId: candidate.version.versionId,
      evidenceRefs: [evidence],
      toolchainFingerprint: 'fake-language-plugin@1.0.0',
      criticalFailures: 1,
      testsPassed: 11,
      testsTotal: 12,
      stability: 0.9,
    }, fixture.config.publicationGate);
    assert.equal(decision.outcome, 'ITERATE');
    await assert.rejects(
      fixture.service.publish(run.runId, candidate.version.versionId, decision.decisionId),
      /only PASS decisions may publish/,
    );
    assert.equal(fixture.service.getKnowledgeVersion(candidate.version.versionId)?.status, 'CANDIDATE');
  } finally {
    fixture.dispose();
  }
});

test('empty behavioral evidence cannot produce a publishable decision', async () => {
  const fixture = createTestComposition();
  try {
    const candidate = await acceptedCandidate(fixture);
    let run = fixture.service.createRun(candidate.version.moduleId, 'local-v1');
    run = fixture.service.transition(run.runId, 'PLANNED');
    run = fixture.service.transition(run.runId, 'GENERATING');
    run = fixture.service.transition(run.runId, 'EVALUATING');
    await assert.rejects(
      fixture.service.recordEvaluation({
        runId: run.runId,
        versionId: candidate.version.versionId,
        evidenceRefs: [],
        toolchainFingerprint: 'fake-language-plugin@1.0.0',
        criticalFailures: 0,
        testsPassed: 0,
        testsTotal: 0,
        stability: 1,
      }, fixture.config.publicationGate),
      /behavioral evaluation requires immutable evidence/,
    );
  } finally {
    fixture.dispose();
  }
});

test('evaluation policy cannot differ from the policy bound to the run', async () => {
  const fixture = createTestComposition();
  try {
    const candidate = await acceptedCandidate(fixture);
    let run = fixture.service.createRun(candidate.version.moduleId, 'local-v1');
    run = fixture.service.transition(run.runId, 'PLANNED');
    run = fixture.service.transition(run.runId, 'GENERATING');
    run = fixture.service.transition(run.runId, 'EVALUATING');
    const evidence = await fixture.artifacts.put(Buffer.from('{}'), 'application/json');
    await assert.rejects(
      fixture.service.recordEvaluation({
        runId: run.runId,
        versionId: candidate.version.versionId,
        evidenceRefs: [evidence],
        toolchainFingerprint: 'fake-language-plugin@1.0.0',
        criticalFailures: 0,
        testsPassed: 1,
        testsTotal: 1,
        stability: 1,
      }, { ...fixture.config.publicationGate, policyId: 'unexpected-lax-policy' }),
      /evaluation policy must match the run policy/,
    );
  } finally {
    fixture.dispose();
  }
});
