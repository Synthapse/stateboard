import type { CostReport, HexPlacement, InfraGraph, SpriteKind, Cloud } from '@stateboard/tf-cost';

/** Empty = same-origin (Vite proxies /api → API). Set VITE_API_URL to call API directly. */
const API_BASE = import.meta.env.VITE_API_URL ?? '';

export type ScanRequest = {
  gitUrl?: string;
  ref?: string;
  localPath?: string;
  fixture?: string;
  terraformRoot?: string;
};

export type DependencyEdge = { from: string; to: string };

export type TerraformVisualization = {
  placements: HexPlacement[];
  edges: DependencyEdge[];
  maxMonthlyUsd: number;
};

export type ArchitectureScanResult = {
  graph: InfraGraph;
  costs: CostReport;
  visualization: TerraformVisualization;
};

export type ArchitectureAnalysis = {
  purpose: string;
  supports: string;
  capabilities: string[];
  workloads: string[];
  risks: string[];
  improvements: string[];
  moduleSplits: string[];
  summary: string;
  model: string;
  source: string;
  configured: boolean;
};

export async function analyzeArchitecture(
  graph: InfraGraph,
  costs: CostReport,
): Promise<ArchitectureAnalysis> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}/api/architecture/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ graph, costs }),
    });
  } catch {
    throw new Error('Cannot reach API — start it with: npm run dev:api');
  }
  if (!res.ok) {
    const err = (await res.json().catch(() => null)) as { error?: string } | null;
    throw new Error(err?.error ?? `Analysis failed (${res.status})`);
  }
  return (await res.json()) as ArchitectureAnalysis;
}

export async function scanArchitecture(body: ScanRequest): Promise<ArchitectureScanResult> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}/api/architecture/scan`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
  } catch {
    throw new Error('Cannot reach API — start it with: npm run dev:api');
  }
  if (!res.ok) {
    if (res.status === 500 || res.status === 502 || res.status === 504) {
      throw new Error('API unavailable — start backend: npm run dev:api (port 5281)');
    }
    const err = (await res.json().catch(() => null)) as { error?: string } | null;
    throw new Error(err?.error ?? `Scan failed (${res.status})`);
  }
  return normalize(await res.json());
}

export async function scanSample(): Promise<ArchitectureScanResult> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}/api/architecture/sample`);
  } catch {
    throw new Error('Cannot reach API — start it with: npm run dev:api');
  }
  if (!res.ok) {
    if (res.status === 500 || res.status === 502 || res.status === 504) {
      throw new Error('API unavailable — start backend: npm run dev:api (port 5281)');
    }
    throw new Error(`Sample scan failed (${res.status})`);
  }
  return normalize(await res.json());
}

/** .NET may serialize Q/R as q/r; ensure HexPlacement shape. */
function normalize(raw: unknown): ArchitectureScanResult {
  const r = raw as ArchitectureScanResult;
  const placements = (r.visualization?.placements ?? []).map((p) => {
    const any = p as HexPlacement & { Q?: number; R?: number };
    return {
      nodeId: any.nodeId ?? (any as { NodeId?: string }).NodeId ?? '',
      q: any.q ?? any.Q ?? 0,
      r: any.r ?? any.R ?? 0,
      cloud: any.cloud as Cloud,
      spriteKind: any.spriteKind as SpriteKind,
      address: any.address,
      monthlyUsd: any.monthlyUsd ?? 0,
    } satisfies HexPlacement;
  });
  return {
    graph: r.graph,
    costs: r.costs,
    visualization: {
      placements,
      edges: r.visualization?.edges ?? [],
      maxMonthlyUsd: r.visualization?.maxMonthlyUsd ?? Math.max(0, ...placements.map((p) => p.monthlyUsd)),
    },
  };
}
