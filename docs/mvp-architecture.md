# Insights — Architecture & MVP

**No product UI required.** Delivery = **Slack / email Digests**.  
Prove web stays optional (infra drill-down only). Legacy Decide/Aureyo UI is **out**.

Target: a **working Digest loop** for one product.

## Architecture (v1)

### Do you need Cloud Run / a standing API?

**MVP Digests: no.** Prefer **Cloud Scheduler → Cloud Function** (or Cloud Run **Job**).  
Weekly/monthly work is batch: wake up, query BQ, post Slack, exit. No always-on API, **no Decide UI**.

| Surface | Runtime | Why |
|---------|---------|-----|
| **Digests (Narrate)** | **Cloud Function** (gen2) or Run Job | Scheduled; pay per run |
| **Prove** | Existing Cloud Run API + web | Optional drill-down — not required for Digests |
| **Decide UI** | **Removed** | Solution does not need a UI |

**Recommendation:** Digest code in `Narrate/` as **library + Function entrypoint**. FastAPI only for local debug if useful.

```
Cloud Scheduler (weekly / monthly)
        │
        ▼
   Cloud Function: digest_run(product, cadence)
        ├─► load InsightsSnapshot (BQ)                 # numbers = truth
        ├─► load latest product_strategy hold          # GTM-like (gtm_structure)
        ├─► GenAI enrich + strategy refresh (Gemini)
        ├─► upsert marts_insights.product_strategy     # every cadence
        └─► email / Slack

BigQuery cognispace
  marts_insights.snapshot_daily
  marts_insights.product_strategy   # living hold per product × cadence
```

**Strategy holds:** shaped like `Narrate/document/MultiAgent/gtm_structure.py` (`GTMStrategy` / `GTMRequest`). Digests **edit and refresh** the hold every cadence. Details: [implement-digests.md](./implement-digests.md).  
**Full system architecture (warehouse → Digests → email):** [insights-architecture.md](./insights-architecture.md).

**Monorepo** (`stateboard` → later `insights`):

| Folder | Deployable | Role |
|--------|------------|------|
| `Narrate/` | Cloud Function `insights-digest` | **Hero** — Digests |
| `Prove/` | `stateboard-api` + web | Optional; keep as-is |
| ~~`Decide/`~~ | — | **Dropped** (no UI) |

Shared contract: **`InsightsSnapshot`** (`schema_version: 1`, `product`, `period`, vital-few metrics).

**Diagram + legacy Narrate routes + Cursor implement notes:** [implement-digests.md](./implement-digests.md)

## MVP definition (done when)

A **Slack message every week** for **one product** with real-ish numbers (fixture → then BQ).

| # | Slice | Done when |
|---|--------|-----------|
| M1 | Snapshot schema + fixture JSON | In Narrate |
| M2 | Template Digest from Snapshot | KPIs/flags text ready |
| M2b | **GenAI enrich (Gemini)** | skim + bullets from Snapshot **+ hold** |
| M2c | **Persist strategy hold** | Upsert `marts_insights.product_strategy` each cadence |
| M3 | Email / Slack send | Enriched message delivered |
| M4 | BQ Snapshot for **one** product | Live metrics |
| M5 | Scheduler → Function weekly | Fires on cognispace |

**Out of MVP:** any business UI, Prove rewrite, email, all three products, Contentsquare, Langfuse, Grafana, standing Narrate HTTP API, long marketing PDFs on the weekly path.

## Suggested build order

1. **M1–M2** template Digest in `Narrate/insights/`  
2. **M2b** `enrich.py` with Gemini (`GEMINI_API_KEY`)  
3. **M3** Slack webhook (Secret Manager)  
4. GA4 (or Billing) → `cognispace` for one product  
5. **M4–M5** BQ + Function + Scheduler  

## Vital-few Snapshot (MVP fields)

- `product`, `period_start`, `period_end`
- Growth: sessions/users, Δ vs prior  
- Cloud $: total (or n/a)  
- Reliability: 0–3 flags  
- `watch`: ≤3 bullets  

## Decisions locked

- Digests = north star (Slack first); **no Decide UI**  
- Monorepo: Narrate + Prove; archive Aureyo/Raporting when green  
- No Ansible — BQ in `terraform/bigquery.tf` (same TF root as Cloud Run)  
- No Grafana for v1  

## Open (Tuesday+)

- Which product first?  
- Slack channel  
- Review BQ structure in Console vs `terraform/bigquery.tf`  
- GA4 already exporting to `cognispace`?
