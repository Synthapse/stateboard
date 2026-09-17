# Insights (monorepo)

**Narrate** (Digests) + **Prove** (optional infra UI). Formerly Stateboard.  
**No Decide / business UI** — delivery is Slack / email only.

**North star:** weekly/monthly Digests from BigQuery for `kih` · `lindle` · `yca`.

## Main doc

**[docs/Analytics & Insights Plan.md](docs/Analytics%20%26%20Insights%20Plan.md)** — product strategy, lenses, questions, warehouse.

**Build / MVP (follow these for implementation):**

| Doc | Purpose |
|-----|---------|
| [docs/mvp-architecture.md](docs/mvp-architecture.md) | Architecture + MVP slices |
| [docs/insights-architecture.md](docs/insights-architecture.md) | System architecture: data flow, benefits, improvements |
| [docs/implement-digests.md](docs/implement-digests.md) | Narrate Digests + GenAI + strategy holds |
| [docs/bigquery-load-paths.md](docs/bigquery-load-paths.md) | How GA4 / Billing / Langfuse load |
| [docs/bigquery-terraform.md](docs/bigquery-terraform.md) | TF datasets/tables |

## Layout

```
Narrate/                # Digest engine → Slack/email (ex Raporting)
Prove/
  web/                  # optional hex map / cost / health
  Stateboard.Api/       # .NET API
  Stateboard.Core/
packages/tf-cost/
docs/                   # Analytics & Insights Plan = main strategy doc
terraform/              # Prove infra + BigQuery structure
```

## Quick start

### Narrate (hero)

```bash
cd Narrate
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # gitignored
# see Narrate/README.md for digest_run smoke tests
```

Secrets: `Narrate/SECRETS.md` · `.env.example`.

### Prove (optional)

```bash
dotnet run --project Prove/Stateboard.Api --urls http://localhost:5281
npm install && npm run dev
```

## Status

- [x] Narrate + Prove in monorepo; Decide UI dropped  
- [x] Main strategy doc in repo (`docs/Analytics & Insights Plan.md`)  
- [ ] Digest M4–M5 (live BQ + Scheduler) — see implement-digests  
- [ ] `terraform apply` for BQ datasets  
- [ ] Archive Aureyo + Raporting when green  

## Deploy

Prove today: `stateboard.synthapse.xyz` / Cloud Run `stateboard-api`.  
See `docs/deploy-gcp.md`.
