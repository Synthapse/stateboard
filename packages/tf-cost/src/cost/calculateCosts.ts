import type {
  CostFamily,
  CostLine,
  CostOptions,
  CostReport,
  InfraGraph,
  InfraNode,
} from '../types.js';
import { classifyFamily } from './classifyFamily.js';
import { bookAsOf, getUnitPrice } from './getUnitPrice.js';

const DEFAULTS = {
  aws: 'us-east-1',
  azure: 'westeurope',
  gcp: 'us-central1',
};

function defaultRegion(node: InfraNode, options: CostOptions): { region: string; usedDefault: boolean } {
  if (node.attrs.region) return { region: node.attrs.region, usedDefault: false };
  if (node.cloud === 'other') return { region: 'global', usedDefault: true };
  const d = options.defaultRegions?.[node.cloud] ?? DEFAULTS[node.cloud];
  return { region: d, usedDefault: true };
}

async function lineForNode(
  node: InfraNode,
  options: CostOptions,
  hours: number,
): Promise<{ line: CostLine; warning?: string }> {
  const family = classifyFamily(node.type);

  if (family === 'free') {
    return {
      line: {
        nodeId: node.id,
        address: node.address,
        cloud: node.cloud,
        family,
        monthlyUsd: 0,
        confidence: 'high',
        basis: 'free / meta resource',
      },
    };
  }

  if (node.cloud === 'other' || family === 'other') {
    return {
      line: {
        nodeId: node.id,
        address: node.address,
        cloud: node.cloud,
        family: family === 'other' ? 'other' : family,
        monthlyUsd: 0,
        confidence: 'unknown',
        basis: 'no pricing rule',
      },
    };
  }

  const { region, usedDefault } = defaultRegion(node, options);
  const sku =
    node.attrs.sku ??
    (family === 'disk' ? 'gp3' : family === 'object' ? 'standard' : family === 'network' ? 'alb' : '');

  if (!sku) {
    return {
      line: {
        nodeId: node.id,
        address: node.address,
        cloud: node.cloud,
        family,
        monthlyUsd: 0,
        confidence: 'low',
        basis: 'missing sku',
      },
    };
  }

  const unitPrice = await getUnitPrice(
    { cloud: node.cloud, family, sku, region },
    options,
  );

  if (!unitPrice) {
    return {
      line: {
        nodeId: node.id,
        address: node.address,
        cloud: node.cloud,
        family,
        monthlyUsd: 0,
        confidence: 'unknown',
        basis: `no price for ${sku} @ ${region}`,
      },
    };
  }

  let monthly = 0;
  let basis = '';
  if (unitPrice.unit === 'hour') {
    monthly = unitPrice.amount * hours;
    if (node.attrs.multiAz) monthly *= 1.5;
    basis = `${sku} · ${region} · $${unitPrice.amount}/h · ${hours}h`;
  } else if (unitPrice.unit === 'gb-month') {
    const gb = node.attrs.storageGb ?? 0;
    monthly = gb * unitPrice.amount;
    basis = `${gb} GB · ${sku} · ${region} · $${unitPrice.amount}/GB-mo`;
  } else {
    monthly = unitPrice.amount;
    basis = `${sku} · ${region} · $${unitPrice.amount}/mo`;
  }

  return {
    line: {
      nodeId: node.id,
      address: node.address,
      cloud: node.cloud,
      family,
      monthlyUsd: monthly,
      confidence: usedDefault ? 'medium' : 'high',
      basis,
      unitPrice,
    },
    warning: usedDefault ? `${node.address}: missing region — used ${region}` : undefined,
  };
}

export async function calculateCosts(
  graph: InfraGraph,
  options: CostOptions = {},
): Promise<CostReport> {
  const hours = options.hoursPerMonth ?? 730;
  const lines: CostLine[] = [];
  const warnings: string[] = [];

  for (const node of graph.nodes) {
    const { line, warning } = await lineForNode(node, options, hours);
    lines.push(line);
    if (warning) warnings.push(warning);
  }

  const byCloud = { aws: 0, azure: 0, gcp: 0, other: 0 };
  const byFamily = {
    compute: 0,
    disk: 0,
    object: 0,
    database: 0,
    network: 0,
    free: 0,
    other: 0,
  } satisfies Record<CostFamily, number>;

  const moduleMap = new Map<string, { monthlyUsd: number; nodeCount: number }>();
  const typeMap = new Map<string, { monthlyUsd: number; nodeCount: number }>();

  for (const line of lines) {
    byCloud[line.cloud] += line.monthlyUsd;
    byFamily[line.family] += line.monthlyUsd;
  }

  for (const node of graph.nodes) {
    const line = lines.find((l) => l.nodeId === node.id)!;
    const m = moduleMap.get(node.modulePath) ?? { monthlyUsd: 0, nodeCount: 0 };
    m.monthlyUsd += line.monthlyUsd;
    m.nodeCount += 1;
    moduleMap.set(node.modulePath, m);

    const t = typeMap.get(node.type) ?? { monthlyUsd: 0, nodeCount: 0 };
    t.monthlyUsd += line.monthlyUsd;
    t.nodeCount += 1;
    typeMap.set(node.type, t);
  }

  const uncoveredCount = lines.filter((l) => l.confidence === 'unknown').length;

  return {
    asOf: bookAsOf(),
    currency: 'USD',
    hoursPerMonth: hours,
    totalMonthlyUsd: lines.reduce((s, l) => s + l.monthlyUsd, 0),
    byCloud,
    byModule: [...moduleMap.entries()].map(([path, v]) => ({ path, ...v })),
    byType: [...typeMap.entries()].map(([type, v]) => ({ type, ...v })),
    byFamily,
    lines,
    uncoveredCount,
    warnings,
  };
}
