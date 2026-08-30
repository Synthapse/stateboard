import type { Cloud, CostReport, InfraGraph, InfraNode, SpriteKind } from './types.js';

export type HexPlacement = {
  nodeId: string;
  q: number;
  r: number;
  cloud: Cloud;
  spriteKind: SpriteKind;
  address: string;
  monthlyUsd: number;
};

const SPIRAL: Array<[number, number]> = (() => {
  const out: Array<[number, number]> = [[0, 0]];
  for (let ring = 1; ring <= 24; ring++) {
    let q = ring;
    let r = -ring;
    const dirs: Array<[number, number]> = [
      [0, 1],
      [-1, 1],
      [-1, 0],
      [0, -1],
      [1, -1],
      [1, 0],
    ];
    for (const [dq, dr] of dirs) {
      for (let i = 0; i < ring; i++) {
        out.push([q, r]);
        q += dq;
        r += dr;
      }
    }
  }
  return out;
})();

function moduleCentroid(index: number, total: number): { cq: number; cr: number } {
  if (total <= 1) return { cq: 0, cr: 0 };
  const angle = (index / total) * Math.PI * 2 - Math.PI / 2;
  const dist = 4 + Math.floor(total / 3);
  return {
    cq: Math.round(Math.cos(angle) * dist),
    cr: Math.round(Math.sin(angle) * dist),
  };
}

/** Pack every infra node onto axial hexes, clustered by module. */
export function layoutResourcesToHex(
  graph: InfraGraph,
  costs?: CostReport | null,
): HexPlacement[] {
  const costById = new Map(costs?.lines.map((l) => [l.nodeId, l.monthlyUsd]) ?? []);
  const modules = [...graph.modules].sort((a, b) => a.path.localeCompare(b.path));
  const used = new Set<string>();
  const placements: HexPlacement[] = [];

  const takeSlot = (cq: number, cr: number): { q: number; r: number } | null => {
    for (const [dq, dr] of SPIRAL) {
      const q = cq + dq;
      const r = cr + dr;
      const key = `${q},${r}`;
      if (used.has(key)) continue;
      used.add(key);
      return { q, r };
    }
    return null;
  };

  modules.forEach((mod, mi) => {
    const { cq, cr } = moduleCentroid(mi, modules.length);
    const nodes = mod.nodeIds
      .map((id) => graph.nodes.find((n) => n.id === id))
      .filter((n): n is InfraNode => !!n);

    for (const node of nodes) {
      const slot = takeSlot(cq, cr);
      if (!slot) continue;
      placements.push({
        nodeId: node.id,
        q: slot.q,
        r: slot.r,
        cloud: node.cloud,
        spriteKind: node.spriteKind,
        address: node.address,
        monthlyUsd: costById.get(node.id) ?? 0,
      });
    }
  });

  return placements;
}
