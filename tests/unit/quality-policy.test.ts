import assert from 'node:assert/strict';
import test from 'node:test';
import { DeterministicQualityPolicy } from '../../packages/application/src/quality-policy.ts';
import { GOOD_BODY } from '../helpers/fixture.ts';

test('quality policy accepts structured and pinned knowledge', () => {
  const report = new DeterministicQualityPolicy(70).evaluate(GOOD_BODY, {
    title: 'Knowledge Gate',
    description: 'Separates document and behavior gates.',
    provenance: [{ path: 'spec.md', commit: 'abc123', pinned: true }],
  });
  assert.equal(report.outcome, 'ACCEPTED');
  assert.ok(report.score >= 70);
});

test('quality policy rejects unsupported prose without provenance', () => {
  const report = new DeterministicQualityPolicy(70).evaluate('short note', {
    title: '', description: '', provenance: [],
  });
  assert.equal(report.outcome, 'REJECTED');
  assert.ok(report.weakPoints.length >= 3);
});
