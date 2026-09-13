import type { SpriteKind } from '@stateboard/tf-cost';

/** Destination groups for Terraform resources — shared map + HUD palette. */
export type ResourceGroup = SpriteKind;

export const GROUP_META: Record<
  ResourceGroup,
  { label: string; short: string; accent: string; fill: string; hexTop: number; hexSide: number }
> = {
  compute: {
    label: 'Compute',
    short: 'CPU',
    accent: '#f59e0b',
    fill: '#3b2a12',
    hexTop: 0x8a6230,
    hexSide: 0x5a3a14,
  },
  database: {
    label: 'Database',
    short: 'DB',
    accent: '#a78bfa',
    fill: '#2a1f3d',
    hexTop: 0x6a4a8a,
    hexSide: 0x3a2858,
  },
  storage: {
    label: 'Storage',
    short: 'STO',
    accent: '#38bdf8',
    fill: '#0f2a3a',
    hexTop: 0x3a6a8a,
    hexSide: 0x1e4a5c,
  },
  network: {
    label: 'Network',
    short: 'NET',
    accent: '#34d399',
    fill: '#0f2e28',
    hexTop: 0x3a7a68,
    hexSide: 0x1e5a48,
  },
  identity: {
    label: 'Identity',
    short: 'IAM',
    accent: '#fb7185',
    fill: '#3a1a24',
    hexTop: 0x8a4a58,
    hexSide: 0x5a2834,
  },
  generic: {
    label: 'Other',
    short: 'TF',
    accent: '#94a3b8',
    fill: '#1e293b',
    hexTop: 0x4a5560,
    hexSide: 0x2a3540,
  },
};

export const GROUP_ORDER: ResourceGroup[] = [
  'compute',
  'database',
  'storage',
  'network',
  'identity',
  'generic',
];
