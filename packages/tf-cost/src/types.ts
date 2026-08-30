export type Cloud = 'aws' | 'azure' | 'gcp' | 'other';

export type CostFamily =
  | 'compute'
  | 'disk'
  | 'object'
  | 'database'
  | 'network'
  | 'free'
  | 'other';

export type SpriteKind =
  | 'compute'
  | 'network'
  | 'storage'
  | 'database'
  | 'identity'
  | 'generic';

export type CostAttrs = {
  region?: string;
  sku?: string;
  storageGb?: number;
  multiAz?: boolean;
};

export type InfraNode = {
  id: string;
  address: string;
  type: string;
  name: string;
  cloud: Cloud;
  provider: string;
  modulePath: string;
  dependencies: string[];
  attrs: CostAttrs;
  spriteKind: SpriteKind;
};

export type InfraGraph = {
  meta: { terraformVersion: string; serial: number; lineage?: string };
  nodes: InfraNode[];
  modules: { path: string; nodeIds: string[] }[];
};

export type UnitPrice = {
  amount: number;
  unit: 'hour' | 'month' | 'gb-month';
  source: 'pricebook' | 'api';
  asOf: string;
};

export type PriceQuery = {
  cloud: Exclude<Cloud, 'other'>;
  family: CostFamily;
  sku: string;
  region: string;
};

export type PriceFetcher = (query: PriceQuery) => Promise<UnitPrice | null>;

export type CostOptions = {
  currency?: 'USD';
  hoursPerMonth?: number;
  defaultRegions?: { aws?: string; azure?: string; gcp?: string };
  priceSource?: 'local' | 'live' | 'local+live';
  fetchPrices?: PriceFetcher;
};

export type CostLine = {
  nodeId: string;
  address: string;
  cloud: Cloud;
  family: CostFamily;
  monthlyUsd: number;
  confidence: 'high' | 'medium' | 'low' | 'unknown';
  basis: string;
  unitPrice?: UnitPrice;
};

export type CostReport = {
  asOf: string;
  currency: 'USD';
  hoursPerMonth: number;
  totalMonthlyUsd: number;
  byCloud: { aws: number; azure: number; gcp: number; other: number };
  byModule: { path: string; monthlyUsd: number; nodeCount: number }[];
  byType: { type: string; monthlyUsd: number; nodeCount: number }[];
  byFamily: Record<CostFamily, number>;
  lines: CostLine[];
  uncoveredCount: number;
  warnings: string[];
};
