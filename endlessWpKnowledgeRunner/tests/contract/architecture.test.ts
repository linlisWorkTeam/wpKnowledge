import assert from 'node:assert/strict';
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';
import test from 'node:test';

function files(root: string): string[] {
  return readdirSync(root).flatMap((name) => {
    const path = join(root, name);
    return statSync(path).isDirectory() ? files(path) : [path];
  });
}

test('domain core has no SDK, database, language, or adapter dependency', () => {
  const source = files('endlessWpKnowledgeRunner/packages/domain/src').map((path) => readFileSync(path, 'utf8')).join('\n');
  for (const forbidden of ['langgraph', 'temporal', 'deepseek', 'dsh', 'sqlite', 'clang', 'gcc', 'packages/adapters']) {
    assert.equal(source.toLowerCase().includes(forbidden), false, `domain contains forbidden dependency: ${forbidden}`);
  }
});

test('application depends on ports and domain, never concrete adapters', () => {
  const source = files('endlessWpKnowledgeRunner/packages/application/src').map((path) => readFileSync(path, 'utf8')).join('\n');
  assert.equal(source.includes('packages/adapters'), false);
  assert.equal(source.includes('../../adapters/'), false);
});

test('LangGraph remains isolated in domain-knowledge infrastructure', () => {
  const application = files('endlessWpKnowledgeRunner/packages/application/src').map((path) => readFileSync(path, 'utf8')).join('\n');
  const infrastructure = files('endlessWpKnowledgeRunner/infrastructure/domain-knowledge/src').map((path) => readFileSync(path, 'utf8')).join('\n');
  assert.equal(application.toLowerCase().includes('@langchain/langgraph'), false);
  assert.match(infrastructure, /@langchain\/langgraph/);
  assert.doesNotMatch(infrastructure, /KnowledgeVersion|PublicationReceipt|EvaluationReport/);
  assert.doesNotMatch(infrastructure, /createServer|\/api\/v1/);
});
