# Plan — Better utilization of gathered Insights data

**Goal:** Use existing marts/core (not new sources) so Digests and daily ops drive decisions.

## Scope

| Phase | Deliverable | Status |
|-------|-------------|--------|
| **A** | Digest **Actions** from existing facts (executive priority + top cloud + top event + gaps) | **Done** |
| **A** | Leaner email: Actions → KPIs → ≤3 Insights → Watch; shorten Strategy | **Done** |
| **A** | Subject line with sessions Δ + cloud $ | **Done** |
| **A** | Gemini: max 3 cross-lens insights | **Done** |
| **B** | Daily red-flag email (reliability down / AI cost gap) from marts already filled | **Done** (`digest_alerts` in `daily_pipeline`) |
| **C** | Looker board on `marts.looker_*` (ops checklist, no new ETL) | Doc only — see below |
| **Ops** | KIH billing export + YCA billing refresh | Console (separate) |

## Email shape (target)

```
SUBJECT: [KIH] Sessions +0.0% · Cloud $0.00

KIH weekly Digest
Period: …

Actions          ← NEW (deterministic from marts/executive)
• …

KPIs + curated extras
Reliability (if any)
Insights (≤3, GenAI cross-lens)
What to watch (≤3)
Strategy hold    ← title + risk only (no long summary paste)
```

## Out of scope this pass

- HTML email templates  
- Slack channel switch  
- New warehouse tables / Contentsquare ETL  
- Full Looker Studio build in GCP console  

## Success check

Manual: `?product=kih&cadence=weekly` → body has **Actions**, ≤3 Insights, subject includes Sessions/Cloud.

Redeploy after code change: `bash Narrate/scripts/deploy_digest_fn.sh`

## Phase C — Looker (ops, no code)

1. Run `?action=looker_views` once if views missing.  
2. Looker Studio → BigQuery → `cognispace` → charts on `marts.looker_growth`, `looker_cost`, `looker_ai`, `looker_reliability`.  
3. One page: growth vs cloud $ by product; reliability up/down.
