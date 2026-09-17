# BigQuery load paths → hub `cognispace`

How raw product data lands in BigQuery, becomes `marts_insights.snapshot_daily`, and feeds Digests.

| Doc | Purpose |
|-----|---------|
| **[ui-setup-load-paths.md](./ui-setup-load-paths.md)** | **What to click in GA4 / Billing Console** (IDs, checklist) |
| [bigquery-terraform.md](./bigquery-terraform.md) | TF datasets/tables |
| [implement-digests.md](./implement-digests.md) | Narrate Digest engine |
| [Analytics & Insights Plan.md](./Analytics%20%26%20Insights%20Plan.md) | Product IDs + strategy |

Code: `Narrate/insights/integrations/products.py` (registry) · `…/bigquery/snapshot_builder.py` (GA4+Billing → Snapshot).

```
GA4 (native daily)          ──► analytics_<property_id>.events_*
GCP Billing (native)        ──► raw_billing.gcp_billing_export_resource_v1_*
Langfuse (API ETL daily)    ──► raw_langfuse.daily_metrics
Clarity (API ETL daily)     ──► raw_clarity.daily_insights (last 1–3 days)
Contentsquare (API signal)  ──► Snapshot flags / watch (UX SoT)
                                        │
                         build_snapshots()
                                        ▼
                         marts_insights.snapshot_daily
```

---

## Implemented load path (code)

| Piece | Role |
|-------|------|
| `integrations/products.py` | KIH / Lindle / YCA → GA4 property, dataset, GCP project, billing account |
| `sql/ga4_growth*.sql` | Sessions / users (+ prior window for Δ) |
| `sql/billing_cost*.sql` | `cloud_cost_usd` / `ai_cost_usd` by `project.id` |
| `snapshot_builder.py` | Runs SQL → inserts `snapshot_daily` |
| `build_snapshots()` | CLI / HTTP `action=build_snapshots` |

```bash
DIGEST_USE_FIXTURE=0 python -c "from insights import build_snapshots, Product; print(build_snapshots(Product.KIH))"
```

---

## Practical load paths (summary)

### 1. GA4 → BigQuery (native) — UI setup required

See [ui-setup-load-paths.md](./ui-setup-load-paths.md) §1.

| Product | Property | Dataset |
|---------|----------|---------|
| kih | `499549002` | `analytics_499549002` |
| lindle | `506154105` | `analytics_506154105` |
| yca | `494547928` | `analytics_494547928` |

### 2. GCP Billing → BigQuery (native) — UI setup required

See [ui-setup-load-paths.md](./ui-setup-load-paths.md) §2. Dataset `raw_billing` in `cognispace`.

### 3. Langfuse / Contentsquare / Clarity

**Included** — see [ui-setup-load-paths.md](./ui-setup-load-paths.md) §§3–5.  
Registry: `integrations/products.py`. Loaders: `integrations/langfuse|contentsquare|clarity/`.

---

## Automation

| Step | Automated? | How |
|------|------------|-----|
| GA4 → BQ | Yes after one-time link | Google daily export |
| Billing → BQ | Yes after one-time export | Google export |
| `snapshot_daily` | Yes after you schedule it | `build_snapshots` cron / Scheduler |
| Digest | Yes (M5) | Scheduler → Function |
| Langfuse | API keys in `.env` | **Daily** `langfuse_etl` → `raw_langfuse.daily_metrics` |
| Contentsquare | Project id + API key | UX signal each Snapshot build |
| Clarity | Project id + token | Legacy signal each Snapshot build |

---

## Env

`DIGEST_USE_FIXTURE=0` · `BQ_PROJECT=cognispace` · `BQ_LOCATION=EU` · ADC / `BQ_CREDENTIALS_PATH`
