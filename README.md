# Stateboard

Terraform state visualizer: **RTS-style hex graphics** + **`@stateboard/tf-cost`** calculation module.

Derived from Ascension Live visuals in [From-Stone-to-Ascension](https://github.com/PiotrZak/From-Stone-to-Ascension) — game simulation stripped; graphics + cost architecture kept.

## Monorepo

| Path | Role |
|------|------|
| `apps/web` | React + Three.js — `/live` graphics lab, `/stateboard` scan + cost UI |
| `packages/tf-cost` | Scan `tfstate`, get unit prices, calculate $/mo by cloud |
| `docs/` | Design notes (`terraform-stateboard.md`, RTS graphics) |

## Quick start

```bash
npm install
npm run dev
```

- http://localhost:5173/ — home  
- http://localhost:5173/live — RTS hex + sprite lab  
- http://localhost:5173/stateboard — paste state → calculate costs  

## Cost module

```ts
import { scanTfState, calculateCosts } from '@stateboard/tf-cost';

const graph = scanTfState(tfstateJson);
const report = await calculateCosts(graph, { priceSource: 'local' });
// report.byCloud.aws | azure | gcp
```

## Org

Maintained under **Synthapse**.
