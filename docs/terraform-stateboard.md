# Terraform Stateboard — Plan

**Codename:** Stateboard  
**Genre:** Infra map — **scan Terraform repo (HCL)** via **.NET API** → **draw** architecture on RTS hex board → **cost** $/mo by cloud  
**Status:** MVP in repo (`src/Stateboard.Api` + `apps/web`)  
**Graphics:** Same family as Ascension Live — hex prisms, billboard sprites, Slate Tactical HUD  

See also [architecture.md](architecture.md).

---

## 1. Product promise

```
git repo with *.tf
    → .NET SCANNER (resources / modules / refs)
    → DRAW architecture on RTS hex map
    → COST MODULE estimates $ / month by cloud
```

| Pillar | Meaning |
|--------|---------|
| **Backend = .NET** | Clone/scan repo, graph + cost JSON |
| **Scan source** | HCL in another repo (not browser-only tfstate paste) |
| **Graphics = RTS** | Hex + sprites |
| **Cost** | Local pricebooks (live APIs later) |

---

## 2. Pipeline

```
┌─────────────┐     ┌────────────────────┐     ┌──────────────────┐
│ 1. SCANNER  │ ──▶ │ 2. COST CALCULATOR │ ──▶ │ 3. RTS RENDERER  │
│ tfstate →   │     │ get prices +       │     │ hex map + HUD $  │
│ InfraGraph  │     │ calculate monthly  │     │ + cost heat      │
└─────────────┘     └────────────────────┘     └──────────────────┘
```

Order matters: **scan → cost → draw** so the map and HUD always have numbers.

---

## 3. Scanner (`scanTfState`)

1. Parse state v3/v4  
2. Expand every `instances[]` (count / for_each)  
3. Detect cloud from provider / type prefix  
4. Extract **cost attrs** (region, SKU, disk GB, …) into `CostAttrs`  
5. Redact secrets  
6. Emit `InfraGraph` (complete node list)

```ts
type InfraNode = {
  id: string;
  address: string;
  type: string;
  name: string;
  cloud: 'aws' | 'azure' | 'gcp' | 'other';
  provider: string;
  modulePath: string;
  dependencies: string[];
  attrs: CostAttrs;
  spriteKind: SpriteKind;
};
```

---

## 4. Cost calculation module (core)

**Package:** `src/TTS.Web/src/terraform/cost/`  
**Export:** `calculateCosts(graph, options) → Promise<CostReport>`

This module is responsible for **getting costs** (unit prices) and **calculating** monthly totals. It is not optional UI sugar.

### 4.1 Responsibilities

| Step | Function | Does |
|------|----------|------|
| 1 | `normalizeAttrs` | Map raw TF attributes → `CostAttrs` (sku, region, gb, …) |
| 2 | `classifyFamily` | Map `aws_instance` → `compute`, etc. |
| 3 | **`getUnitPrice`** | **Get** $/hour or $/GB-month from price book and/or live API |
| 4 | `computeMonthly` | Family formula → monthly USD + basis string |
| 5 | `aggregate` | Totals by cloud / module / type / family |

### 4.2 API

```ts
function calculateCosts(
  graph: InfraGraph,
  options?: CostOptions,
): Promise<CostReport>;

type CostOptions = {
  currency?: 'USD';
  hoursPerMonth?: number;          // default 730
  defaultRegions?: { aws?: string; azure?: string; gcp?: string };
  /** How CostCalculator gets unit prices */
  priceSource?: 'local' | 'live' | 'local+live';
  fetchPrices?: PriceFetcher;      // required when live / hybrid
};

/** Gets a unit price for one SKU — local book or network. */
type PriceFetcher = (query: PriceQuery) => Promise<UnitPrice | null>;

type PriceQuery = {
  cloud: 'aws' | 'azure' | 'gcp';
  family: CostFamily;
  sku: string;
  region: string;
};

type UnitPrice = {
  amount: number;
  unit: 'hour' | 'month' | 'gb-month';
  source: 'pricebook' | 'api';
  asOf: string;
};

type CostFamily =
  | 'compute'
  | 'disk'
  | 'object'
  | 'database'
  | 'network'
  | 'free'
  | 'other';

type CostLine = {
  nodeId: string;
  address: string;
  cloud: 'aws' | 'azure' | 'gcp' | 'other';
  family: CostFamily;
  monthlyUsd: number;
  confidence: 'high' | 'medium' | 'low' | 'unknown';
  basis: string;                 // "m5.large · us-east-1 · $0.096/h · 730h"
  unitPrice?: UnitPrice;
};

type CostReport = {
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
```

### 4.3 How it **gets** unit prices (`getUnitPrice`)

```
getUnitPrice(query)
  │
  ├─ priceSource === 'local'
  │     → read pricebooks/{aws|azure|gcp}.json
  │
  ├─ priceSource === 'live'
  │     → await fetchPrices(query)   // cloud retail / price list APIs
  │
  └─ priceSource === 'local+live'
        → try fetchPrices; on null/fail → local book
```

**Local price books** (MVP — always ship these):

```
cost/pricebooks/
  meta.json     # schemaVersion, generatedAt
  aws.json      # compute[region][sku]=$/h, disk[region].gbMonth, database[…], network.flat[…]
  azure.json
  gcp.json
```

**Live getters** (Phase C — same `PriceFetcher`):

| Cloud | Adapter gets prices from |
|-------|---------------------------|
| AWS | Price List / Bulk API (or CI-cached export) |
| Azure | Retail Prices API |
| GCP | Cloud Billing Catalog API |

UI always labels output **Estimate**, with `asOf` + confidence.

### 4.4 How it **calculates** monthly cost

```
for each InfraNode:
  family = classifyFamily(node.type)
  attrs  = normalizeAttrs(node)
  price  = await getUnitPrice({ cloud, family, sku: attrs.sku, region })
  line   = familyCalculator[family](attrs, price, hoursPerMonth)
aggregate(lines) → CostReport
```

| Family | Gets from state | Calculation |
|--------|-----------------|-------------|
| **compute** | instance/vm/machine type, region | `unitPrice.hourly × hoursPerMonth` |
| **disk** | size_gb, disk type, region | `gb × gbMonthPrice` |
| **object** | stored gb if known | `gb × gbMonthPrice` (else low/unknown) |
| **database** | class/sku/tier, multi-AZ | SKU monthly (× factor if multi-AZ) |
| **network** | lb / nat / gateway | flat $/mo from book or API |
| **free** | iam, random_*, many meta resources | `$0`, high confidence |
| **other** | unmatched types | `$0`, unknown → `uncoveredCount++` |

Family calculators live in separate files:

```
cost/
  calculateCosts.ts          # orchestrator
  getUnitPrice.ts            # local + live dispatch
  normalizeAttrs.ts
  classifyFamily.ts
  aggregate.ts
  families/
    compute.ts
    disk.ts
    object.ts
    database.ts
    network.ts
    free.ts
  pricebooks/
    aws.json
    azure.json
    gcp.json
  fetchers/                  # Phase C
    awsPriceFetcher.ts
    azurePriceFetcher.ts
    gcpPriceFetcher.ts
```

### 4.5 Per-cloud rollup (primary)

After lines exist:

```
byCloud.aws   = sum(lines where cloud === 'aws')
byCloud.azure = …
byCloud.gcp   = …
byCloud.other = …
```

Also `byModule`, `byType`, `byFamily` for the Cost panel and filters.

### 4.6 Wire-up

```ts
const graph = scanTfState(json);
const costs = await calculateCosts(graph, {
  priceSource: 'local',           // later: 'local+live'
  hoursPerMonth: 730,
  defaultRegions: {
    aws: 'us-east-1',
    azure: 'westeurope',
    gcp: 'us-central1',
  },
});
createStateboardMap(host, graph, costs);
```

| Consumer | Uses |
|----------|------|
| Top HUD | `totalMonthlyUsd`, `byCloud.*` |
| Cost panel | `byModule`, `byFamily`, `uncoveredCount` |
| Map heat | `lines[nodeId].monthlyUsd` |
| Detail dock | `basis`, `confidence`, `unitPrice` |

### 4.7 Tests for the cost module

| Case | Expect |
|------|--------|
| AWS `t3.micro` in book | monthly ≈ hourly × 730, high |
| Missing region | default region, medium + warning |
| IAM user | $0 high, not uncovered |
| Mixed aws + azurerm + google | three `byCloud` buckets |
| Unknown type | uncovered++, unknown |
| `local+live` with fetcher null | falls back to book |

### 4.8 Cost module build phases

| Phase | Deliverable |
|-------|-------------|
| **C0** | Types + `calculateCosts` stub |
| **C1** | `getUnitPrice` local + AWS compute/disk/db books |
| **C2** | Azure + GCP family parity |
| **C3** | Aggregations + warnings + bind HUD/map |
| **C4** | Live `PriceFetcher` adapters (get costs from APIs) |
| **C5** | CI refresh of pricebooks |

---

## 5. RTS renderer (`createStateboardMap`)

Same graphics as `/live`:

- Hex board, module continents, cloud tint  
- Sprites for every scanned node  
- Selection ring, dep paths  
- HUD / heat from `CostReport`  

| Live RTS | Stateboard |
|----------|------------|
| Unit sprite | Resource instance |
| Team wash | Cloud (AWS / Azure / GCP) |
| Height / glow | Cost heat from calculator |
| Top Res/Energy | **$ total + by cloud** from `CostReport` |
| HP bar | Relative cost vs peers (optional) |

---

## 6. Layout (draw entire infra)

1. Cluster by module → pack all nodes onto hexes  
2. Root = capital beacon  
3. Stack identical types only when N is huge (display-only; scan+cost still per instance)  

---

## 7. UI

| Region | Content |
|--------|---------|
| Top | Serial · TF version · **$ total/mo** · AWS · Azure · GCP |
| Map | Full infra sprites |
| Cost panel | From `CostReport` (by cloud / module / family) |
| Dock | Selection + **cost basis** from calculator |
| Roster | Type filters |

---

## 8. Architecture (files)

```
src/TTS.Web/src/terraform/
  scanTfState.ts
  cost/                    # ← calculation module (get + calculate)
    calculateCosts.ts
    getUnitPrice.ts
    … (see §4.4)
  layoutHex.ts
  tfSprites.ts
  fixtures/sample.tfstate
src/TTS.Web/src/components/stateboard/
  createStateboardMap.ts
  StateboardView.tsx
  CostPanel.tsx
route: /stateboard
```

---

## 9. Overall phased build

| Phase | Focus |
|-------|--------|
| **S0** | Plan |
| **S1** | Scanner |
| **S2** | **Cost module C1–C3** (get local prices + calculate + aggregate) |
| **S3** | RTS draw all nodes |
| **S4** | Bind costs to HUD / heat / dock |
| **S5** | Deps, filters, stacks |
| **S6** | Plan overlay · remote state · **live price fetch (C4)** |

---

## 10. Risks

| Risk | Mitigation |
|------|------------|
| Estimate ≠ invoice | Label Estimate; confidence; show `basis` |
| Stale books | `asOf` in UI; CI refresh (C5) |
| Secrets in state | Redact in scanner |
| API rate / auth for live get | Optional; local default |

---

## 11. Success criteria

1. Scan full state  
2. Draw full estate with RTS graphics  
3. **Cost module gets prices and calculates** monthly USD with **by-cloud** split  
4. User can open a resource and see **how** the number was calculated (`basis`)

---

## Open questions

1. Default regions when attrs missing?  
2. USD only for MVP?  
3. Ship live `getUnitPrice` in first release or local books only?  

---

## 12. Repo decision — new repo or not?

### Short answer

| Piece | Where | New repo? |
|-------|--------|-----------|
| **Cost calculation module** (`calculateCosts`, pricebooks, fetchers) | **Own small package / repo** | **Yes — recommended** |
| RTS hex + sprite UI (Stateboard map) | Stay with or next to TTS.Web graphics | No (reuse Live) |
| Thin `/stateboard` page | This monorepo **or** a small web app that depends on both | Optional |

**Do make a new repo (or at least a standalone package) for the calculation module.**  
**Do not** put price logic only inside the game client — it should be importable without Three.js / TTS.

### Why a separate cost package/repo

1. **No game dependency** — cost math is pure TS; Ascension Live graphics are not  
2. **Reusable** — CLI (`stateboard cost --state file`), CI, other UIs can call the same module  
3. **Versioned pricebooks** — release `@you/tf-cost` independently when AWS/Azure/GCP prices refresh  
4. **Clear testing** — fixture states + expected `$` without standing up Vite/WebGL  
5. **IP boundary** — game fiction stays in From-Stone-to-Ascension; infra tooling can be public/private on its own  

### Recommended layout

```
GitHub/
  From-Stone-to-Ascension/          # game + /live graphics lab
    src/TTS.Web/src/components/live/
    src/TTS.Web/src/components/stateboard/   # map UI only (optional later)

  tf-cost/                          # NEW REPO — calculation module
    package.json                    # name: @…/tf-cost
    src/
      scanTfState.ts                # optional: keep scan here too
      cost/
        calculateCosts.ts
        getUnitPrice.ts
        families/
        pricebooks/
        fetchers/
    tests/
    README.md
```

**Stateboard app options:**

| Option | When |
|--------|------|
| **A. Web stays in TTS monorepo** | Fastest: `/stateboard` imports `@…/tf-cost` + reuses Live graphics | Good for prototype |
| **B. New `stateboard` web repo** | Product should not live under the game | Better if you ship to infra users |
| **C. Monorepo workspace later** | `apps/stateboard` + `packages/tf-cost` + `packages/hex-graphics` | When both grow |

### What goes in the new `tf-cost` repo

- `scanTfState` (or accept already-scanned graph)  
- **`calculateCosts` / `getUnitPrice`**  
- Price books + live fetchers  
- CLI: `npx tf-cost estimate --state terraform.tfstate` → JSON `CostReport`  
- Tests + pricebook refresh script  

### What stays out of `tf-cost`

- Three.js, hex map, sprites, React HUD  
- Game / TTS.Core  

### Practical recommendation for you

1. **Create new repo `tf-cost`** for the calculation module (scan + get prices + calculate).  
2. **Keep graphics in this repo** for now (`/live` → later `/stateboard` UI).  
3. Wire UI with `npm`/`pnpm` dependency (or git submodule / workspace link) on `tf-cost`.  
4. If Stateboard becomes a real product for others, split the web app out (option B); keep consuming `tf-cost`.

**You do not need a new repo for the RTS graphics** — only for the **cost calculation module** (and optionally scan).  
