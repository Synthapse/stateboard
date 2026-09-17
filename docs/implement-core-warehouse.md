# Core warehouse — implement checklist

How empty `core.*` / `marts.*` shells get filled. Digests still use `marts_insights.snapshot_daily`.

Related: [Analytics & Insights Plan.md](./Analytics%20%26%20Insights%20Plan.md) · [bigquery-terraform.md](./bigquery-terraform.md)

## Source matrix

| Table | Source | Needs app DB? | Code |
|-------|--------|---------------|------|
| `core.dim_product` | `products.py` seed | No | `core_seed.py` |
| `core.dim_feature` | Taxonomy seed × product + GA4 observed events + usage | No | `core_seed.py` + `ga4_core.py` |
| `core.dim_service` | Inventory deployables + synced GCP billing services | No | `core_seed.py` + `billing_core.py` |
| `core.dim_gcp_service` | `raw_billing` × product | No | `billing_core.py` |
| `core.fct_gcp_cost` | `raw_billing` | No | `billing_core.py` |
| `marts.cost` | from `fct_gcp_cost` | No | `billing_core.py` |
| `core.dim_model` | `raw_langfuse.daily_metrics` | No | `langfuse_core.py` |
| `core.fct_llm_traces` | `raw_langfuse.daily_metrics` | No | `langfuse_core.py` |
| `marts.ai` | Langfuse ETL promote | No | `marts_ai.py` |
| `core.fct_healthchecks` | HTTP probes | No | `healthchecks.py` |
| `core.fct_exceptions` | Health fails + Error Reporting | No | `healthchecks.py` |
| `raw_health.probes` / `.exceptions` | Landing for probes/exceptions | No | `healthchecks.py` |
| `staging.stg_service_health` / `stg_exceptions` | Staging promote | No | `healthchecks.py` |
| `marts.reliability` | from health + exceptions | No | `healthchecks.py` |
| `core.fct_sessions` | GA4 `events_*` daily | No | `ga4_core.py` |
| `core.fct_events` | GA4 event_name counts | No | `ga4_core.py` |
| `marts.growth` | sessions/users (+ day delta) | No | `ga4_core.py` |
| `marts.product` | top events / totals | No | `ga4_core.py` |
| `marts.customer` | DAU + 7d engagement proxy | No | `ga4_core.py` |
| `core.dim_user` | App DBs | **Yes** | `integrations/app/` |
| `core.dim_account` | App DBs | **Yes** | `integrations/app/` |
| `raw_app.entities` | App extract landing | Yes | `app/writer.py` |

## App DB env

| Product | Env | Notes |
|---------|-----|-------|
| KIH | `KIH_DATABASE_URL` | Postgres; local Docker must be up (`host.docker.internal` → `127.0.0.1`) |
| YCA | `YCA_DATABASE_URL` | Postgres |
| Lindle | `LINDLE_NEO4J_URI`, `_USER`, `_PASSWORD`, `_DATABASE` | Neo4j Aura |

PHI-safe: no passwords/tokens; emails partially redacted; no clinical fields.

Extractors: `app/kih_sql.py`, `app/yca_sql.py`, `app/lindle_neo4j.py` (+ shared `sql_extract.py`).

## Commands

```bash
cd Narrate
DIGEST_USE_FIXTURE=0 python -c "from insights import core_seed; print(core_seed())"
DIGEST_USE_FIXTURE=0 python -c "from insights import billing_core; print(billing_core())"
DIGEST_USE_FIXTURE=0 python -c "from insights import langfuse_core; print(langfuse_core())"
DIGEST_USE_FIXTURE=0 python -c "from insights import app_extract; print(app_extract())"
DIGEST_USE_FIXTURE=0 python -c "from insights import healthchecks; print(healthchecks())"
DIGEST_USE_FIXTURE=0 python -c "from insights import ga4_core; print(ga4_core())"
DIGEST_USE_FIXTURE=0 python -c "from insights import looker_views; print(looker_views())"
DIGEST_USE_FIXTURE=0 python -c "from insights import executive_summary; print(executive_summary())"
```

HTTP (Cloud Function): `?action=…` · `executive` · `daily_pipeline` (runs executive after snapshots)

Looker Studio: [looker-marts.md](./looker-marts.md) (`marts.looker_*` views).

### GenAI executive layer

Consumes finalized `snapshot_daily` + marts (growth/product/customer/ai/cost/reliability),
asks Gemini for portfolio direction + ranked priorities (facts-only), writes `marts.executive`
(`product=portfolio` + per-product priority slices). Fail-open stub if `GEMINI_API_KEY` unset.

Override probe URLs: `HEALTH_URL_KIH_DR_KIWI_APP=https://…/health` (pattern `HEALTH_URL_<PRODUCT>_<SERVICE>`).

## Later (not in this pass)

- `fct_orders` / `fct_subscriptions`
- Full dbt project
- True WAU/MAU (needs raw user_pseudo_id retention, not daily sum)
