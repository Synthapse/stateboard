import { detectCloud, spriteKindFor } from './detectCloud.js';
import type { CostAttrs, InfraGraph, InfraNode } from './types.js';

const SECRET_KEY = /password|secret|private_key|access_key|token/i;

function redact(attrs: Record<string, unknown>): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(attrs)) {
    out[k] = SECRET_KEY.test(k) ? '[redacted]' : v;
  }
  return out;
}

function pickAttrs(type: string, raw: Record<string, unknown>): CostAttrs {
  const a: CostAttrs = {};
  const region =
    (raw.region as string) ||
    (raw.location as string) ||
    (raw.availability_zone as string)?.replace(/[a-z]$/, '');
  if (region) a.region = String(region);

  const sku =
    (raw.instance_type as string) ||
    (raw.vm_size as string) ||
    (raw.size as string) ||
    (raw.machine_type as string) ||
    (raw.instance_class as string) ||
    (raw.sku_name as string);
  if (sku) a.sku = String(sku);

  const gb = raw.size ?? raw.disk_size_gb ?? raw.volume_size;
  if (typeof gb === 'number') a.storageGb = gb;
  if (typeof gb === 'string' && !Number.isNaN(Number(gb))) a.storageGb = Number(gb);

  if (raw.multi_az === true || raw.high_availability === true) a.multiAz = true;

  // touch type so unused-param lint stays quiet in some configs
  void type;
  return a;
}

type TfResource = {
  module?: string;
  mode?: string;
  type: string;
  name: string;
  provider: string;
  instances?: Array<{
    index_key?: string | number;
    attributes?: Record<string, unknown>;
    dependencies?: string[];
  }>;
};

export function scanTfState(input: unknown): InfraGraph {
  const state = input as {
    version?: number;
    terraform_version?: string;
    serial?: number;
    lineage?: string;
    resources?: TfResource[];
  };

  const resources = state.resources ?? [];
  const nodes: InfraNode[] = [];

  for (const res of resources) {
    if (res.mode && res.mode !== 'managed') continue;
    const modulePath = res.module ?? '';
    const cloud = detectCloud(res.type, res.provider ?? '');
    const instances = res.instances?.length ? res.instances : [{ attributes: {} }];

    for (const inst of instances) {
      const idx = inst.index_key;
      const suffix = idx === undefined ? '' : `[${JSON.stringify(idx).replace(/^"|"$/g, '')}]`;
      const address = `${modulePath ? modulePath + '.' : ''}${res.type}.${res.name}${suffix}`;
      const rawAttrs = redact((inst.attributes ?? {}) as Record<string, unknown>);
      const id = address;
      nodes.push({
        id,
        address,
        type: res.type,
        name: res.name,
        cloud,
        provider: res.provider ?? '',
        modulePath,
        dependencies: inst.dependencies ?? [],
        attrs: pickAttrs(res.type, rawAttrs),
        spriteKind: spriteKindFor(res.type),
      });
    }
  }

  const moduleMap = new Map<string, string[]>();
  for (const n of nodes) {
    const list = moduleMap.get(n.modulePath) ?? [];
    list.push(n.id);
    moduleMap.set(n.modulePath, list);
  }

  return {
    meta: {
      terraformVersion: state.terraform_version ?? 'unknown',
      serial: state.serial ?? 0,
      lineage: state.lineage,
    },
    nodes,
    modules: [...moduleMap.entries()].map(([path, nodeIds]) => ({ path, nodeIds })),
  };
}
