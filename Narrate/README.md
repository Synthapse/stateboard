# Narrate

Digest engine: **load BQ data** → GenAI enrich (BQ details) → living **GTM strategy hold** → **email** (Slack later).

Clean Architecture under `insights/`. Legacy FastAPI PDF routes (`main.py` / `raports/`) are **parked**.

## Layout

```
insights/
  domain/            # Product, Snapshot, ProductStrategyHold (extends GTMStrategy)
  application/       # LoadDigestData, DigestRunUseCase, render, bq_details
  integrations/      # BigQuery client + Snapshot/Strategy loaders
  infrastructure/    # fixture/BQ repos (adapters), Gemini, email/Slack
  entrypoints/       # digest_run, digest_run_all, digest_http, daily_pipeline
```

### Integrations (load data)

| Module | Role |
|--------|------|
| `integrations/bigquery/client.py` | BQ client (ADC or `BQ_CREDENTIALS_PATH`) |
| `integrations/bigquery/snapshot_builder.py` | **GA4 + Billing → `snapshot_daily`** |
| `integrations/langfuse/daily_etl.py` | Langfuse API → `raw_langfuse.daily_metrics` |
| `integrations/langfuse/marts_ai.py` | **Promote → `marts.ai`** |
| `integrations/products.py` | product → GA4/Billing/GCP IDs |

**UI setup:** [docs/ui-setup-load-paths.md](../docs/ui-setup-load-paths.md)

```bash
DIGEST_USE_FIXTURE=0 python -c "from insights import build_snapshots, Product; print(build_snapshots(Product.LINDLE))"
DIGEST_USE_FIXTURE=0 python -c "from insights import digest_run, Product; print(digest_run(Product.LINDLE)['text'])"
```

## Quick start

```bash
cd Narrate
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt   # or: uv pip install -r requirements.txt
cp .env.example .env
```

### Env (see `.env.example`)

| Var | Purpose |
|-----|---------|
| `DIGEST_USE_FIXTURE` | `1` fixtures / `0` BigQuery |
| `BQ_PROJECT` / `BQ_LOCATION` | cognispace / EU |
| `DIGEST_CHANNEL` | `email` (default) or `slack` |
| `SMTP_*` / `DIGEST_EMAIL_TO_*` | send mail |
| `GEMINI_API_KEY` / `DIGEST_GENAI` | GenAI enrich |
| `LANGFUSE_*` | AI cost ETL → `marts.ai` |

## marts.ai (Langfuse)

```bash
# ETL yesterday + promote marts.ai
DIGEST_USE_FIXTURE=0 python -c "from insights import langfuse_etl; print(langfuse_etl(lookback_days=7))"

# Or promote existing raw_langfuse rows only
DIGEST_USE_FIXTURE=0 python -c "from insights.integrations.langfuse.marts_ai import promote_marts_ai; print(promote_marts_ai(lookback_days=30))"
```

```sql
SELECT period_date, product, metrics_json
FROM `cognispace.marts.ai`
ORDER BY period_date DESC LIMIT 20;
```

## M5 — Cloud Function + Scheduler

```bash
# 1) Fill Narrate/.env (SMTP, Gemini, Langfuse, DIGEST_EMAIL_TO_*, …)
# 2) Deploy Function — script packs .env into Function env (no values printed)
bash scripts/deploy_digest_fn.sh

# 3) Put URL into terraform.tfvars:
#    digest_function_url = "https://….cloudfunctions.net/insights-digest"
# 4) terraform apply  → daily 06:00 + weekly Mon 07:00 (Europe/Warsaw)
```

| Schedule | Action |
|----------|--------|
| Daily 06:00 | `?action=daily_pipeline&all=1` → Langfuse + Clarity + marts + Snapshots |
| Weekly Mon 07:00 | `?all=1&cadence=weekly` → Digests × 3 |

Local smoke for the same pipeline:

```bash
DIGEST_USE_FIXTURE=0 python -c "from insights import daily_pipeline; print(daily_pipeline())"
```

## Status

| Slice | Status |
|-------|--------|
| M1–M4 Snapshot + Digests | Done |
| marts.ai from Langfuse | Done (promote on ETL) |
| M5 Function + Scheduler | Deploy script + TF — run deploy + apply |

Docs: [strategy](../docs/strategy-recommendation.md) · [architecture](../docs/insights-architecture.md) · [setup](../docs/ui-setup-load-paths.md)

## Secrets

[SECRETS.md](./SECRETS.md) — never commit keys / SA JSON / SMTP passwords.
