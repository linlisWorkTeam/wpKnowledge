import assert from 'node:assert/strict';
import { mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';
import {
  DeepSeekHarnessHeadlessAgent, type DeepSeekHarnessAuditRecord,
} from '../../packages/adapters/deepseek-harness-agent/src/index.ts';

const OUTPUT_SCHEMA = {
  type: 'object', required: ['answer'], additionalProperties: false,
  properties: { answer: { type: 'string', minLength: 1 } },
};

function request(workspaceRoot: string) {
  return {
    role: 'doc-gen', prompt: '生成结构化结果。', outputSchema: OUTPUT_SCHEMA,
    idempotencyKey: 'run-1:doc-gen:0', workspaceRoot,
    metadata: { runId: 'run-1', iteration: 0 },
  };
}

test('DeepSeek Harness provider validates structured output and emits a redacted audit record', async () => {
  const workspace = mkdtempSync(join(tmpdir(), 'wp-dsh-agent-'));
  const script = join(workspace, 'fake-dsh.mjs');
  writeFileSync(script, `
const prompt = process.argv.at(-1);
if (!prompt.includes('JSON Schema') || !prompt.includes('run-1:doc-gen:0')) process.exit(8);
process.stdout.write(JSON.stringify({ answer: 'validated' }));
`);
  const audits: DeepSeekHarnessAuditRecord[] = [];
  try {
    const provider = new DeepSeekHarnessHeadlessAgent({
      command: process.execPath, args: [script], allowedWorkspaceRoots: [workspace],
      onAudit: (record) => { audits.push(record); },
    });
    const output = await provider.run(request(workspace));
    assert.deepEqual(output, { answer: 'validated' });
    assert.equal(audits.length, 1);
    assert.equal(audits[0]?.status, 'SUCCEEDED');
    assert.equal(audits[0]?.role, 'doc-gen');
    assert.match(audits[0]?.promptSha256 ?? '', /^[a-f0-9]{64}$/);
    assert.equal(JSON.stringify(audits[0]).includes('生成结构化结果'), false);
  } finally {
    rmSync(workspace, { recursive: true, force: true });
  }
});

test('DeepSeek Harness provider selects the last schema-valid object from a duplicated final answer', async () => {
  const workspace = mkdtempSync(join(tmpdir(), 'wp-dsh-agent-duplicated-'));
  const script = join(workspace, 'fake-dsh.mjs');
  writeFileSync(script, `process.stdout.write('{"wrong":true}\\n\\n{"answer":"last-valid"}\\n');\n`);
  try {
    const provider = new DeepSeekHarnessHeadlessAgent({
      command: process.execPath, args: [script], allowedWorkspaceRoots: [workspace],
    });
    assert.deepEqual(await provider.run(request(workspace)), { answer: 'last-valid' });
  } finally {
    rmSync(workspace, { recursive: true, force: true });
  }
});

test('DeepSeek Harness provider ignores unmatched quotes in CLI diagnostics before JSON', async () => {
  const workspace = mkdtempSync(join(tmpdir(), 'wp-dsh-agent-diagnostics-'));
  const script = join(workspace, 'fake-dsh.mjs');
  const output = 'diagnostic: model said "unfinished\n{"answer":"valid-after-log"}\n';
  writeFileSync(script, `process.stdout.write(${JSON.stringify(output)});\n`);
  try {
    const provider = new DeepSeekHarnessHeadlessAgent({
      command: process.execPath, args: [script], allowedWorkspaceRoots: [workspace],
    });
    assert.deepEqual(await provider.run(request(workspace)), { answer: 'valid-after-log' });
  } finally {
    rmSync(workspace, { recursive: true, force: true });
  }
});

test('DeepSeek Harness provider fails closed on schema-invalid model output', async () => {
  const workspace = mkdtempSync(join(tmpdir(), 'wp-dsh-agent-invalid-'));
  const script = join(workspace, 'fake-dsh.mjs');
  writeFileSync(script, `process.stdout.write(JSON.stringify({ wrong: true }));\n`);
  try {
    const provider = new DeepSeekHarnessHeadlessAgent({
      command: process.execPath, args: [script], allowedWorkspaceRoots: [workspace],
    });
    await assert.rejects(provider.run(request(workspace)), /AGENT_OUTPUT_INVALID/);
  } finally {
    rmSync(workspace, { recursive: true, force: true });
  }
});

test('DeepSeek Harness provider denies workspaces outside the deployment allowlist', async () => {
  const allowed = mkdtempSync(join(tmpdir(), 'wp-dsh-agent-allowed-'));
  const denied = mkdtempSync(join(tmpdir(), 'wp-dsh-agent-denied-'));
  try {
    const provider = new DeepSeekHarnessHeadlessAgent({
      command: process.execPath, args: ['-e', 'process.stdout.write(`{}`)'],
      allowedWorkspaceRoots: [allowed],
    });
    await assert.rejects(provider.run(request(denied)), /DSH_AGENT_WORKSPACE_DENIED/);
  } finally {
    rmSync(allowed, { recursive: true, force: true });
    rmSync(denied, { recursive: true, force: true });
  }
});
