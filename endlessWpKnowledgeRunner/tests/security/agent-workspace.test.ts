import assert from 'node:assert/strict';
import { existsSync, mkdtempSync, mkdirSync, readFileSync, rmSync, symlinkSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';
import { LocalAgentWorkspace } from '../../packages/adapters/agent-workspace/src/index.ts';

test('role workspace copies only the explicit readable-path allowlist', async () => {
  const root = mkdtempSync(join(tmpdir(), 'wp-agent-view-'));
  const source = join(root, 'source');
  const views = join(root, 'views');
  mkdirSync(join(source, 'src'), { recursive: true });
  writeFileSync(join(source, 'src', 'secret.ts'), 'REFERENCE_SECRET');
  writeFileSync(join(source, 'src', 'public.ts'), 'export interface Public {}');
  try {
    const provider = new LocalAgentWorkspace({ workspaceRoot: views, allowedSourceRoots: [source] });
    const view = await provider.materialize({
      isolationKey: 'run:code:0', role: 'code', sourceRoot: source,
      readablePaths: ['src/public.ts'],
    });
    assert.equal(readFileSync(join(view.workspaceRoot, 'src', 'public.ts'), 'utf8'), 'export interface Public {}');
    assert.equal(existsSync(join(view.workspaceRoot, 'src', 'secret.ts')), false);
    assert.deepEqual(view.readablePaths, ['src/public.ts']);
    assert.match(readFileSync(join(view.workspaceRoot, '.flywheel-workspace.json'), 'utf8'), /"role": "code"/);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test('role workspace rejects traversal and source symlinks', async () => {
  const root = mkdtempSync(join(tmpdir(), 'wp-agent-view-deny-'));
  const source = join(root, 'source');
  const outside = join(root, 'outside.txt');
  mkdirSync(source);
  writeFileSync(outside, 'not allowed');
  symlinkSync(outside, join(source, 'linked.txt'));
  try {
    const provider = new LocalAgentWorkspace({ workspaceRoot: join(root, 'views'), allowedSourceRoots: [source] });
    await assert.rejects(provider.materialize({
      isolationKey: 'traversal', role: 'code', sourceRoot: source, readablePaths: ['../outside.txt'],
    }), /AGENT_WORKSPACE_PATH_DENIED/);
    await assert.rejects(provider.materialize({
      isolationKey: 'symlink', role: 'code', sourceRoot: source, readablePaths: ['linked.txt'],
    }), /AGENT_WORKSPACE_SYMLINK_DENIED/);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});
