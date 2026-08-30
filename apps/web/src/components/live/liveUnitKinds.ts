/** Live RTS unit kinds — visual tokens matching rts-mode.md / concept sheet. */

export type LiveUnitKind =
  | 'pioneer'
  | 'drone'
  | 'cyber'
  | 'firewall'
  | 'battery'
  | 'swarm'
  | 'agent'
  | 'bio'
  | 'nano';

export type LiveBuildingKind = 'capital' | 'outpost' | 'lab';

export type LiveTeam = 'orange' | 'steel';

export const TEAM_COLORS: Record<LiveTeam, number> = {
  orange: 0xec6a06,
  steel: 0x6b8cae,
};

export const ERA_ACCENT = {
  tts4: 0x4cd7f6,
  tts5: 0xa78bfa,
  tts6: 0x2dd4bf,
} as const;

export type LiveUnitPlacement = {
  id: string;
  kind: LiveUnitKind;
  team: LiveTeam;
  q: number;
  r: number;
  hp: number;
  stack?: number;
  selected?: boolean;
};

export type LiveBuildingPlacement = {
  id: string;
  kind: LiveBuildingKind;
  team: LiveTeam;
  q: number;
  r: number;
};

export const UNIT_LABELS: Record<LiveUnitKind, string> = {
  pioneer: 'Pioneer',
  drone: 'Patrol drone',
  cyber: 'Cyber team',
  firewall: 'Firewall node',
  battery: 'Strike battery',
  swarm: 'Autonomic swarm',
  agent: 'Agent cell',
  bio: 'Bio-strike',
  nano: 'Nano cloud',
};
