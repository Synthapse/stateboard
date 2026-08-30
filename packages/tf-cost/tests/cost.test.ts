import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { calculateCosts, scanTfState, SAMPLE_TFSTATE } from '../src/index.ts';

describe('tf-cost', () => {
  it('scans sample and estimates by cloud', async () => {
    const graph = scanTfState(SAMPLE_TFSTATE);
    assert.equal(graph.nodes.length, 4);
    const costs = await calculateCosts(graph, { priceSource: 'local' });
    assert.ok(costs.byCloud.aws > 0);
    assert.ok(costs.totalMonthlyUsd > 0);
    const iam = costs.lines.find((l) => l.address.includes('aws_iam_user'));
    assert.equal(iam?.monthlyUsd, 0);
    assert.equal(iam?.confidence, 'high');
  });
});
