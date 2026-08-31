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
    const page = await fetch(`${base}/`);
    assert.equal(page.status, 200);
    assert.match(await page.text(), /可验证知识控制台/);
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
