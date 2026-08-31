# Stateboard

Scan a **Terraform repository** → build an **architecture graph** → draw it on an **RTS hex map** → estimate **cloud cost**.

Backend is **.NET**. The web app only renders.

## Architecture

```
Git repo / local path / fixture
        │
        ▼
┌──────────────────────┐
│  Stateboard.Api (.NET)│
│  • shallow git clone  │
│  • scan *.tf (HCL)    │
│  • cost pricebook     │
└──────────┬───────────┘
           │ JSON graph + costs
           ▼
┌──────────────────────┐
│  apps/web (React)     │
│  RTS hex visualization│
└──────────────────────┘
```

| Path | Role |
|------|------|
| `src/Stateboard.Api` | ASP.NET Core API |
| `src/Stateboard.Core` | HCL scan, git clone, cost calc |
| `fixtures/sample-terraform` | Demo infra |
| `apps/web` | RTS map UI |
| `packages/tf-cost` | Shared TS types / layout helpers (optional client tools) |

## Quick start

Terminal 1 — API:

```bash
dotnet run --project src/Stateboard.Api --urls http://localhost:5281
```

Terminal 2 — UI:

```bash
npm install
npm run dev
```

- http://localhost:5173/stateboard — paste an external git URL or load the sample  
- Pipeline: **clone → HCL scan → cost module → hex visualization**  
- `POST /api/architecture/scan` `{ "gitUrl": "https://github.com/org/repo" }`  
  returns `graph`, `costs`, and `visualization` (placements + dependency edges)

## Deploy (GCP + GitHub Actions)

Production target: **`stateboard.synthapse.xyz`** (GCS + Cloudflare) and **`api.stateboard.synthapse.xyz`** (Cloud Run).

See **[docs/deploy-gcp.md](docs/deploy-gcp.md)** for Terraform, GitHub secrets/variables, and Cloudflare DNS.

## How repo → map works

1. API clones the repo (shallow) or reads a local/fixture path.  
2. Walks all `*.tf` files (skips `.terraform/`).  
3. Extracts `resource` blocks, module folders, SKU/region attrs, and cross-refs (`aws_vpc.main.id`, `module.network…`).  
4. Builds `InfraGraph` + `CostReport`.  
5. Web lays nodes on hexes (by module cluster) and draws sprites + cost bars.

This is **source architecture** (HCL), not live cloud inventory. Remote state / `terraform plan` can be added later as another scan mode.

## Org

Maintained under **Synthapse**.
