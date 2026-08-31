# Architecture — repo scan + cost + visualization

## Pipeline (all on .NET)

```
gitUrl (external repo)
  → GitRepoFetcher (shallow clone, 2m timeout, GitHub URL normalize)
  → TerraformRootFinder (auto-detect terraform/infra/…)
  → TerraformHclScanner (*.tf → InfraGraph)
  → CostCalculationModule (pricebooks → CostReport)
  → HexLayoutEngine (placements + dependency edges)
  → React RTS map
```

## Modules

| Module | Path | Role |
|--------|------|------|
| Scan | `Scanning/` | Clone + HCL parse |
| Cost | `Cost/CostCalculationModule` | Unit prices → $/mo |
| Visualization | `Visualization/HexLayoutEngine` | Hex board + edges |

## API

| Method | Path | Notes |
|--------|------|--------|
| GET | `/api/health` | |
| GET | `/api/architecture/sample` | fixture scan |
| POST | `/api/architecture/scan` | `{ gitUrl, ref?, terraformRoot? }` |
| POST | `/api/cost/calculate` | recompute cost for a graph |

Response includes `graph`, `costs`, and `visualization` (`placements`, `edges`, `maxMonthlyUsd`).
