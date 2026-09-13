# Insights — Architecture & MVP

Target for next week: a **working Digest loop** for one product, not a full Decide/Prove rewrite.

## Architecture (v1)

```
Cloud Scheduler (weekly)
        │
        ▼
   Narrate  POST /v1/insights/digest/run
        │  product=kih|lindle|yca  cadence=weekly|monthly
        ├─► load InsightsSnapshot (BQ or fixture)
        ├─► render short Digest text (+ optional LLM “what to watch”)
        └─► Slack webhook  (email = phase 1.5)

BigQuery hub: cognispace
  raw_ga4_* · raw_billing · marts_* · (later langfuse / reliability)

Prove  = drill-down UI/API when Digest flags cost/health
Decide = on-demand / history (after Digest works)
```

**One monorepo** (`stateboard` → later `insights`):

| Folder | Deployable | MVP role |
|--------|------------|----------|
| `Narrate/` | Cloud Run `narrate` | **MVP hero** — Digest engine |
| `Prove/` | existing `stateboard-api` + web | Optional link / cost skim later |
| `Decide/` | hosting later | Out of MVP |

Shared contract: **`InsightsSnapshot`** (`schema_version: 1`, `product`, `period`, vital-few metrics).

## MVP definition (done when)

You get a **Slack message every week** for **one product** with real-ish numbers (BQ or honest fixture → BQ).

| # | Slice | Done when |
|---|--------|-----------|
| M1 | Snapshot schema + fixture JSON | Pydantic/OpenAPI in Narrate |
| M2 | `POST /v1/insights/digest/run` | Returns Digest text from fixture |
| M3 | Slack send | Message in a channel |
| M4 | BQ Snapshot for **one** product | Fixture replaced for that product |
| M5 | Cloud Scheduler weekly | Job hits Narrate on cognispace |

**Out of MVP:** Decide UI polish, Prove hex rewrite, email, monthly cadence, all three products, Contentsquare, Langfuse, Grafana.

## Suggested build order (next week)

1. **M1–M2** in `Narrate/` (local uvicorn)  
2. **M3** Slack Incoming Webhook (Secret Manager)  
3. **Warehouse:** GA4 export → `cognispace` for the chosen product (or Billing if GA4 blocked)  
4. **M4** query → Snapshot  
5. **M5** deploy Narrate + Scheduler  

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

## Open (decide Monday)

- Which product first?  
- Slack workspace / channel  
- GA4 property already exporting to `cognispace`? (yes/no)
