# Insights — Digests design (implementers)

## System diagram (current target)

```
                    ┌─────────────────────────────────────┐
                    │  Delivery = email NOW → Slack later │
                    │  (no product UI)                    │
                    └──────────────────┬──────────────────┘
                                       │
              ┌────────────────────────┼────────────────────────┐
              ▼                        ▼                        ▼
        ┌──────────┐            ┌─────────────┐           ┌──────────┐
        │  Digest  │            │   Narrate   │           │  Prove   │
        │ (inbox)  │◄───────────│  (engine)   │           │(optional)│
        └──────────┘   send     │ Cloud Fn    │           │ Run+web  │
                                └──────┬──────┘           └────┬─────┘
                                       │                       │
              ┌────────────────────────┼───────────────────────┤
              ▼                        ▼                       ▼
         Snapshot                 GenAI enrich            Notifier
         + Strategy hold          (Gemini)              email|slack
              │                        │
              │    ┌───────────────────┘
              │    │ refresh hold each cadence
              ▼    ▼
       ┌─────────────────┐
       │ BigQuery        │
       │ cognispace      │
       │ snapshot_daily  │
       │ product_strategy│  ← living GTM-like holds (kih|lindle|yca)
       └─────────────────┘

~~Decide / Aureyo UI~~  REMOVED — do not build or wire a frontend
```

| Name | What it is now | Build? |
|------|----------------|--------|
| **Narrate** | Digest engine + strategy holds + GenAI enrich | **Yes — MVP hero** |
| **Prove** | Map/cost API+web | Optional |
| **Decide** | Was Aureyo UI | **No — deleted** |

**Products:** `Product` enum — `kih` | `lindle` | `yca`.

**BQ load paths (GA4 / Billing → Snapshot, automation):** [bigquery-load-paths.md](./bigquery-load-paths.md).  
**Console / GA4 UI checklist:** [ui-setup-load-paths.md](./ui-setup-load-paths.md).  
**System architecture (data flow, benefits, roadmap):** [insights-architecture.md](./insights-architecture.md).

---

## Clean Architecture (implemented)

```
Narrate/insights/
  domain/
    models.py          # Product, Cadence, InsightsSnapshot,
                       # ProductStrategyHold (extends GTMStrategy), Enrichment
    ports.py           # SnapshotRepository, StrategyRepository, …
  application/
    load_digest_data.py   # LoadDigestData — Snapshot + strategy together
    bq_details.py         # Enrichment.details from Snapshot
    render_digest.py
    refresh_strategy.py
    digest_run.py
  integrations/
    bigquery/
      client.py           # ADC / SA client
      config.py
      snapshot_loader.py  # load InsightsSnapshot from BQ
      strategy_loader.py  # load/save ProductStrategyHold
  infrastructure/
    fixture_*_repo.py
    bq_*_repo.py          # thin adapters over integrations (+ fixture fallback)
    gemini_*.py
    email_notifier.py / slack_notifier.py
    wiring.py
  entrypoints/
    handler.py
```

**Dependency rule:** `entrypoints` → `application` → `domain` ← `infrastructure`.

**Delivery switch:** `DIGEST_CHANNEL=email` (default) | `slack`.

**Audiences (email):** set per product in `Narrate/.env` — see [ui-setup-load-paths.md](./ui-setup-load-paths.md) §7.

| Env | Purpose |
|-----|---------|
| `DIGEST_EMAIL_TO` | Fallback |
| `DIGEST_EMAIL_TO_KIH` / `_LINDLE` / `_YCA` | Product audiences (comma-separated OK) |

Sends are logged to `marts_insights.digest_delivery`.

---

## Product strategy holds (reuses `gtm_structure.py`, in BigQuery)

**Reuse (not a copy):** `ProductStrategyHold` **extends** `GTMStrategy` and uses `GTMSection` /
`GTMRequest` from `document/MultiAgent/gtm_structure.py`. Helpers:
`to_gtm_strategy()`, `to_gtm_request()`, `from_gtm(...)`. Gemini refresh validates as `GTMStrategy`.

### Shape (`ProductStrategyHold`)

Inherited from `GTMStrategy` / `GTMSection`:

- `title`, `executive_summary`
- `market_analysis` … `risk_mitigation`

Plus Digest metadata + `GTMRequest` seeds: `product`, `cadence`, `period_date`,
`product_description`, `target_market`, `budget_range`, `timeline_constraints`,
`updated_at`, `refreshed_by`.

Monthly `gtm_gen` can take `hold.to_gtm_request()` / `hold.to_gtm_strategy()`.

### BigQuery

| Table | Role |
|-------|------|
| `marts_insights.snapshot_daily` | Vital-few metrics (source of truth for numbers) |
| `marts_insights.product_strategy` | Latest GTM-like hold per `product` × `cadence` (append + read latest) |

Declared in `terraform/bigquery.tf`. Digests **read** the latest hold, **edit** it during the run, **upsert** (append row) every cadence.

### Who edits the hold?

| Actor | When |
|-------|------|
| Seed fixtures / first insert | Bootstrap |
| `SnapshotStrategyRefresher` | Fallback when Gemini off/fails — summary, risk, budget from Snapshot |
| `GeminiStrategyRefresher` | **Done** — rewrites sections; fail-open to template |
| Legacy `gtm_gen` (optional later) | Deep monthly rewrite into the same hold shape |

Reports **own** the narrative text; BQ metrics **own** the numbers.

---

## Digest pipeline

```
digest_run(product, cadence)
   → SnapshotRepository.get_latest()
   → StrategyRepository.get()              # prior GTM hold
   → DigestEnricher.enrich(snapshot, hold) # GeminiEnricher (fail-open)
   → StrategyRefresher.refresh(...)        # GeminiStrategyRefresher → template fallback
   → StrategyRepository.upsert(hold)       # write back every cadence
   → render_digest(snapshot, strategy, enrichment)
   → DigestNotifier.send(...)              # email now / Slack later
```

**Hard rules**

1. Metrics from BQ/fixture only — LLM must not invent sessions/cost.
2. Strategy hold may be rewritten; still cite Snapshot numbers only.
3. Gemini down → template refresh + send (degraded).
4. No Decide UI.

---

## Generative AI — enrichment + strategy refresh (extend)

### Role
Short weekly inbox report + **edit** the living GTM hold — not legacy multi-agent PDFs.

### Model
- **Primary:** Gemini (`GEMINI_API_KEY`)
- Optional: xAI/Grok — later

### Placement

| Layer | Module | Responsibility |
|-------|--------|----------------|
| domain | `Enrichment` | `details` (BQ facts) + `watch_bullets` + `executive_skim` |
| app | `bq_details.py` | Builds `details` from Snapshot only |
| domain | `DigestEnricher` | narrative cites BQ details |
| domain | `StrategyRefresher` | edit `ProductStrategyHold` sections |
| infra | `gemini_enricher.py` | **Done** — GenAI skim/bullets; details always from BQ |
| infra | `gemini_strategy_refresher.py` | **Done** — fail-open section rewrite |
| infra | `noop_enricher.py` | BQ details only when GenAI off |
| app | `SnapshotStrategyRefresher` | template fallback |

### Prompt contract (strategy refresh)

> You are a product strategist. Prior hold + Snapshot JSON are given.  
> Update GTM sections. Use ONLY Snapshot numbers. Output full `ProductStrategyHold` JSON.  
> Keep section titles stable. Max ~120 words per section content.

### Reuse legacy

| Legacy | Use? |
|--------|------|
| `gtm_structure` / `gtm_gen` | Shape inspiration + optional monthly deep rewrite into `product_strategy` |
| FastAPI `/go-to-market` | **PARK** — don’t call from Scheduler |

---

## Status vs MVP slices

| # | Slice | Status |
|---|--------|--------|
| M1 | Snapshot schema + fixtures (3 products) | **Done** |
| M2 | Clean Architecture + `digest_run` | **Done** |
| M2s | GTM-like `ProductStrategyHold` + BQ table + refresh/upsert | **Done** |
| M2b | GenAI enrich + GenAI strategy refresher (fail-open) | **Done** |
| M3a | Email (`piotrzak77@gmail.com`) | **Done** (SMTP to send) |
| M3b | Slack switch | Adapter ready |
| M4 | Live BQ | **Done** |
| M5 | Scheduler → Function (`digest_run_all` / `daily_pipeline`) | **Code + TF ready** — deploy_digest_fn.sh + apply |

**marts.ai:** Langfuse ETL promotes `raw_langfuse.daily_metrics` → `marts.ai` (see `integrations/langfuse/marts_ai.py`).


---

## Legacy Narrate HTTP — PARK

| Method | Path | Status |
|--------|------|--------|
| POST | `/multiAgentDoc`, `/generateDocument`, `/generateSummarization` | PARK |
| GET | `/getAuthenticScopeSpecs` | PARK / DELETE |
| POST | `/marketing-strategy`, `/early-adopter-strategy`, `/go-to-market`, `/brief` | KEEP generators; PARK routes |

CF entry: `insights.entrypoints.handler.digest_http`.

---

## What to do next (Cursor)

1. Set `GEMINI_API_KEY` + SMTP (or Slack) in `Narrate/.env` — never commit.
2. `terraform apply` for `product_strategy` table; seed one row per product in BQ.
3. M4: `DIGEST_USE_FIXTURE=0` with live warehouse rows.
4. M5: `bash Narrate/scripts/deploy_digest_fn.sh` then set `digest_function_url` in tfvars + `terraform apply`.
5. marts.ai: filled by `langfuse_etl` / `action=marts_ai` promote.

### Don’t

- Rebuild Decide UI · invent metrics in LLM · block send if Gemini down · Ansible for BQ · legacy PDF routes as Digest API  

### Local smoke

```bash
cd Narrate
# template path (no key): DIGEST_GENAI=0 or unset GEMINI_API_KEY
python -c "from insights import digest_run, Product; r=digest_run(Product.KIH); print(r['enriched'], r['strategy_refreshed_by']); print(r['text'])"

# all products
python -c "from insights import digest_run_all; print([x['product'] for x in digest_run_all()])"
```

---

## Prove vs Narrate

- **Narrate** = metrics + living strategy hold + GenAI → inbox  
- **Prove** = infra/cost map when Digest flags something  
