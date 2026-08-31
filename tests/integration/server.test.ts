import assert from 'node:assert/strict';
import { once } from 'node:events';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';
import { createKnowledgeServer } from '../../apps/runner/src/server.ts';
import { GOOD_BODY } from '../helpers/fixture.ts';

test('HTTP adapter rejects missing credentials and accepts authenticated candidates', async () => {
  const runtimeDir = mkdtempSync(join(tmpdir(), 'wp-server-'));
  const instance = createKnowledgeServer({ runtimeDir, writeToken: 'test-secret' });
  instance.server.listen(0, '127.0.0.1');
  await once(instance.server, 'listening');
  const address = instance.server.address();
  assert.ok(address && typeof address === 'object');
  const base = `http://127.0.0.1:${address.port}`;
  try {
    const health = await fetch(`${base}/health`);
    assert.equal(health.status, 200);
    assert.equal((await fetch(`${base}/api/v1/status`)).status, 200);
    const denied = await fetch(`${base}/api/v1/ingest`, {
      method: 'POST', headers: { 'content-type': 'application/json' }, body: '{}',
    });
    assert.equal(denied.status, 401);
    const accepted = await fetch(`${base}/api/v1/ingest`, {
      method: 'POST',
      headers: { 'content-type': 'application/json', authorization: 'Bearer test-secret' },
      body: JSON.stringify({
        moduleId: 'server-card', body: GOOD_BODY, title: 'Server Card',
        description: 'Authenticated candidate ingestion.',
        provenance: [{ path: 'specs/README.md', commit: 'abc123', pinned: true }],
      }),
    });
    assert.equal(accepted.status, 201);
    const payload = await accepted.json();
    assert.equal(payload.version.status, 'CANDIDATE');
    const defaultQuery = await fetch(`${base}/api/v1/query?q=${encodeURIComponent('行为')}`);
    assert.equal((await defaultQuery.json()).hits.length, 0);
    const allStatusQuery = await fetch(`${base}/api/v1/query?q=${encodeURIComponent('行为')}&status=`);
    const allStatusPayload = await allStatusQuery.json();
    assert.equal(allStatusPayload.hits.length, 1);
    assert.equal(allStatusPayload.hits[0].status, 'CANDIDATE');
    const page = await fetch(`${base}/`);
    assert.equal(page.status, 200);
    assert.match(await page.text(), /可验证知识控制台/);

    const authHeaders = { 'content-type': 'application/json', authorization: 'Bearer test-secret' };
    const post = (path: string, input: Record<string, unknown>) => fetch(`${base}${path}`, {
      method: 'POST', headers: authHeaders, body: JSON.stringify(input),
    });
    const createdRun = await post('/api/v1/runs', { moduleId: 'server-card', policyId: 'local-v1' });
    assert.equal(createdRun.status, 201);
    const runId = String((await createdRun.json()).runId);
    for (const state of ['PLANNED', 'GENERATING', 'EVALUATING']) {
      const transition = await post('/api/v1/transition', { runId, state });
      assert.equal(transition.status, 200, await transition.text());
    }
    const evidenceRef = await instance.composition.artifacts.put(Buffer.from('{"passed":true}'), 'application/json');
    const evaluated = await post('/api/v1/evaluate', {
      runId, versionId: payload.version.versionId, evidenceRefs: [evidenceRef],
      toolchainFingerprint: 'server-test@1', criticalFailures: 0,
      testsPassed: 1, testsTotal: 1, stability: 1,
    });
    const evaluatedPayload = await evaluated.json();
    assert.equal(evaluated.status, 201, JSON.stringify(evaluatedPayload));
    const decision = evaluatedPayload.decision;
    assert.equal(decision.outcome, 'PASS');
    assert.equal(instance.composition.repository.getRun(runId)?.state, 'REVIEWING');
    const published = await post('/api/v1/publish', {
      runId, versionId: payload.version.versionId, decisionId: decision.decisionId,
    });
    assert.equal(published.status, 201, await published.text());
    assert.equal(instance.composition.service.getKnowledgeVersion(payload.version.versionId)?.status, 'VERIFIED');
  } finally {
    instance.server.close();
    await once(instance.server, 'close');
    rmSync(runtimeDir, { recursive: true, force: true });
  }
});

test('HTTP mutation API is disabled when no write token is configured', async () => {
  const runtimeDir = mkdtempSync(join(tmpdir(), 'wp-server-disabled-'));
  const instance = createKnowledgeServer({ runtimeDir });
  instance.server.listen(0, '127.0.0.1');
  await once(instance.server, 'listening');
  const address = instance.server.address();
  assert.ok(address && typeof address === 'object');
  try {
    const response = await fetch(`http://127.0.0.1:${address.port}/api/v1/ingest`, {
      method: 'POST', headers: { 'content-type': 'application/json' }, body: '{}',
    });
    assert.equal(response.status, 503);
    assert.equal((await response.json()).error, 'WRITE_API_DISABLED');
  } finally {
    instance.server.close();
    await once(instance.server, 'close');
    rmSync(runtimeDir, { recursive: true, force: true });
  }
});
