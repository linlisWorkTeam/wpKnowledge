import assert from 'node:assert/strict';
import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import test from 'node:test';

const componentRoot = 'endlessWpKnowledgeRunner';

function markdownFiles(root: string): string[] {
  return readdirSync(root).flatMap((name) => {
    const path = join(root, name);
    return statSync(path).isDirectory()
      ? markdownFiles(path)
      : path.endsWith('.md')
        ? [path]
        : [];
  });
}

test('Knowledge Flywheel implementation remains under its component root', () => {
  for (const retiredRoot of ['acceptance', 'apps', 'docs', 'packages', 'specs', 'tests', 'workpanel']) {
    assert.equal(existsSync(retiredRoot), false, `root-level ${retiredRoot}/ must not be reintroduced`);
  }
  for (const required of [
    'acceptance/ohmyworkpanel/scenario.json',
    'apps/runner/src/server.ts',
    'docs/ARCHITECTURE.md',
    'packages/domain/src/index.ts',
    'specs/README.md',
    'tests/integration/server.test.ts',
    'web/index.html',
    'runner.config.json',
  ]) {
    assert.equal(existsSync(join(componentRoot, required)), true, `missing component path: ${required}`);
  }
});

test('active component and consolidated WorkPanel documents have valid relative links', () => {
  const documents = [
    'README.md',
    join(componentRoot, 'README.md'),
    'knowledge/3.workpanel/README.md',
    ...markdownFiles(join(componentRoot, 'docs')),
    ...markdownFiles(join(componentRoot, 'specs')),
    'knowledge/3.workpanel/调研/WorkPanel综合分析报告.md',
    'knowledge/3.workpanel/调研/2026-08-31-P0-A知识飞轮可行性评审.md',
    'knowledge/3.workpanel/调研/2026-09-01-PR11知识飞轮交付测评.md',
    'knowledge/3.workpanel/证据/2026-08-31-P0-A评审证据.md',
    'knowledge/3.workpanel/证据/2026-09-01-ohMyWorkPanel真实源码验收.md',
    'knowledge/3.workpanel/证据/2026-09-01-PR11开发复验记录.md',
  ];
  const linkPattern = /\[[^\]]+\]\(([^)]+)\)/g;
  for (const document of documents) {
    const markdown = readFileSync(document, 'utf8');
    for (const match of markdown.matchAll(linkPattern)) {
      const rawTarget = match[1].split('#', 1)[0].replace(/^<|>$/g, '');
      if (!rawTarget || rawTarget.includes('://') || rawTarget.startsWith('mailto:')) continue;
      const target = resolve(dirname(document), decodeURIComponent(rawTarget));
      assert.equal(existsSync(target), true, `broken link in ${document}: ${match[1]}`);
    }
  }
});
