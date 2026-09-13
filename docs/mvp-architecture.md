# Insights — Architecture & MVP

Target for next week: a **working Digest loop** for one product, not a full Decide/Prove rewrite.

## Architecture (v1)

### Do you need Cloud Run / a standing API?

**MVP Digests: no.** Prefer **Cloud Scheduler → Cloud Function** (or Cloud Run **Job**).  
Weekly/monthly work is batch: wake up, query BQ, post Slack, exit. No need for an always-on server.

| Surface | Runtime | Why |
|---------|---------|-----|
| **Digests (Narrate logic)** | **Cloud Function** (gen2) or Run Job | Scheduled; pay per run; simplest |
| **Prove** | Keep existing **Cloud Run** API + web | Already live; interactive map/cost |
| **Decide “Generate now”** | Add HTTP later (Function **or** small Run service) | Only when UI needs on-demand |

**Recommendation:** put Digest code in `Narrate/` as a **library + Function entrypoint** (`main.py` / `digest_handler`). Keep FastAPI optional for local/dev. Promote to a shared HTTP API only if Decide/Prove both call Narrate often.

```
Cloud Scheduler (weekly)
        │
        ▼
   Cloud Function: digest_run(product, cadence)
        ├─► load InsightsSnapshot (BQ or fixture)
        ├─► render Digest (+ optional LLM “what to watch”)
        └─► Slack webhook  (email = phase 1.5)

BigQuery hub: cognispace
  raw_ga4_* · raw_billing · marts_* · (later langfuse / reliability)

Prove  = existing Run API (drill-down) — not required for Digest MVP
Decide = static/Firebase hosting later — not required for Digest MVP
```

**One monorepo** (`stateboard` → later `insights`):

| Folder | Deployable | MVP role |
|--------|------------|----------|
| `Narrate/` | **Cloud Function** `insights-digest` | **MVP hero** |
| `Prove/` | existing `stateboard-api` + web | Unchanged; optional later |
| `Decide/` | hosting later | Out of MVP |

Shared contract: **`InsightsSnapshot`** (`schema_version: 1`, `product`, `period`, vital-few metrics).

## MVP definition (done when)

You get a **Slack message every week** for **one product** with real-ish numbers (BQ or honest fixture → BQ).

| # | Slice | Done when |
|---|--------|-----------|
| M1 | Snapshot schema + fixture JSON | Pydantic/OpenAPI in Narrate |
| M2 | `digest_run` callable (Function handler or local CLI) | Returns Digest text from fixture |
| M3 | Slack send | Message in a channel |
| M4 | BQ Snapshot for **one** product | Fixture replaced for that product |
| M5 | Cloud Scheduler → Function weekly | Job fires on cognispace |

**Out of MVP:** Decide UI polish, Prove hex rewrite, email, monthly cadence, all three products, Contentsquare, Langfuse, Grafana, **standing Narrate Cloud Run API**.

## Suggested build order (next week)

1. **M1–M2** in `Narrate/` (local: `python -m digest` or tiny FastAPI for debug only)  
2. **M3** Slack Incoming Webhook (Secret Manager)  
3. **Warehouse:** GA4 export → `cognispace` for the chosen product (or Billing if GA4 blocked)  
4. **M4** query → Snapshot  
5. **M5** deploy **Function** + Scheduler (not Cloud Run unless you already prefer it)  

Pick **one** product first: recommend `kih` or `lindle` (whichever has cleaner GA4 in BQ already).

## Vital-few Snapshot (MVP fields)

Minimum for Digest body:

- `product`, `period_start`, `period_end`
- Growth: sessions (or users), Δ vs prior period  
- Cloud $: total (if Billing ready; else omit with “n/a”)  
- Reliability: 0–3 flags (optional text)  
- `watch`: up to 3 bullets (LLM or template)

## Decisions already locked

- Monorepo: HOLD stateboard; REMOVE Aureyo + Raporting after green  
- Digests = north star (Slack first)  
- No fourth repo; no Grafana for v1  
- **No Ansible** — BigQuery structure lives in `terraform/bigquery.tf`  
- **Not everything needs Terraform** — Digest = Function + Scheduler (can be `gcloud` deploy); Prove TF stays for existing API/frontend; **BQ datasets/tables = Terraform**

## Infra scope

| Piece | Tool | Notes |
|-------|------|--------|
| BQ datasets + `marts_insights.snapshot_daily` | **Terraform** (`terraform/bigquery.tf`) | Source of truth for structure |
| GA4 / Billing **export linking** | Console (or TF transfer later) | Google-managed table shapes in `raw_*` |
| Digest Function + Scheduler | `gcloud` or small TF later | Not required day-one in TF |
| Prove API / frontend bucket | Existing TF | Keep |
| Ansible | **Do not use** | No servers to configure for Digests/BQ |

## Open (decide Monday)

- Which product first?  
- Slack workspace / channel  
- GA4 property already exporting to `cognispace`? (yes/no)  
- `terraform apply` for BQ datasets (after review `terraform/bigquery.tf`)
