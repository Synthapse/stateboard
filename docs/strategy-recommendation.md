# Strategy Recommendation — Insights (kih · lindle · yca)

**Status:** north star (2026-09-17)

Hub: **`cognispace`** · Delivery: **email Digests** · Runtime: **Cloud Function + Scheduler** · No product UI.

---

## Recommendation

**Double down on Digests as the product.** Do not rebuild Decide/Aureyo. Do not expand Grafana/dbt/full UX warehouse until weekly Digests are trusted and billing is complete.

| Do | Don’t |
|----|--------|
| Use **existing marts** (Actions, Insights, daily alerts) | Collect more sources first |
| Finish **KIH billing** + refresh **YCA billing** | Treat $0 / stale cost as truth |
| One **Looker** board on `marts.looker_*` | Charts in email or a new UI |
| Keep **Prove** optional | Mix Prove into Digest MVP |

**Success:** Monday Digests for kih/lindle/yca with real cloud $, AI $, growth, reliability.

---

## Already live

| Layer | State |
|-------|--------|
| Warehouse | `raw_*` → `core` → `marts` + `marts_insights` |
| Digests | Actions + ≤3 Insights + lean email + smart subject |
| Daily | Langfuse → billing/GA4/Clarity → health → snapshots → executive → alerts |
| Weekly | Mon 07:00 Warsaw → 3 Digests |
| GA4 | `events_*` for all three |
| Billing | Lindle OK · YCA stale · KIH missing export |

Details: [insights-architecture.md](./insights-architecture.md) · Setup: [ui-setup-load-paths.md](./ui-setup-load-paths.md)

---

## Pillars

1. **Inbox first** — weekly Digests = default UI (Actions → KPIs → Insights → Watch → short risk).  
2. **Reuse marts** — growth, product, customer, cost, ai, reliability, executive.  
3. **FinOps honesty** — KIH export → `dr-kiwi-app.raw_billing`; YCA stage must stay fresh.  
4. **Prove is side path** — infra map/cost, not Digest critical path.

---

## Roadmap

**P0:** KIH billing export · YCA billing freshness · Monday audience check  
**P1:** Looker board · Langfuse pricing · alert tuning  
**P2:** revenue/orders later · Slack · monthly cadence · dbt only if needed  

**Non-goals (90 days):** Decide UI · full Clarity marts · mobile portal · email→custom web app  

---

## Docs (essential only)

| Doc | Role |
|-----|------|
| **This file** | Strategy |
| [insights-architecture.md](./insights-architecture.md) | How the system works |
| [ui-setup-load-paths.md](./ui-setup-load-paths.md) | Console / keys checklist |
