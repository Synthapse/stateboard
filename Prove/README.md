# Prove

Platform drill-down — Terraform → architecture graph → hex map, plus cloud cost / health (Insights D–E).

Legacy: **Stateboard**.

## Layout

| Path | Role |
|------|------|
| `web/` | React UI (hex map, cost, health) |
| `Stateboard.Api/` | ASP.NET Core API |
| `Stateboard.Core/` | HCL scan, cost, visualization |

## Run

From repo root:

```bash
dotnet run --project Prove/Stateboard.Api --urls http://localhost:5281
npm install && npm run dev
```

Or web only:

```bash
cd Prove/web && npm run dev
```

## Deploy

Cloud Run `stateboard-api` + GCS frontend (GitHub Actions). See workflows under `.github/workflows/`.
