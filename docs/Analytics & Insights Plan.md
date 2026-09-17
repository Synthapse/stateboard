---
tags: [analytics, observability, gcp, ga4, clarity, langfuse, llm, rag, bigquery, billing, finops, dbt, grafana, product-intelligence]
status: plan
updated: 2026-09-13
covers: [Lindle, CzatBudowlany, KeepItHealthy / Dr Kiwi]
repo_doc: main
---

# Product Intelligence — Analytics & Insights plan

> **Repo main strategy doc** (copied into this monorepo).  
> **Current build truth:** no Decide UI — Digests = Slack/email via **Narrate**; **Prove** = optional infra drill-down.  
> Implement: [mvp-architecture.md](./mvp-architecture.md) · [implement-digests.md](./implement-digests.md) · [bigquery-load-paths.md](./bigquery-load-paths.md) · [ui-setup-load-paths.md](./ui-setup-load-paths.md) · [bigquery-terraform.md](./bigquery-terraform.md)

> **You are building a product** that delivers insights across your platforms (YCA / Lindle / Dr Kiwi) — not only a private ops spreadsheet.  
> **BigQuery (`cognispace`) is the warehouse.** GA4, Contentsquare, Langfuse, GCP app data, Billing, and health/jobs are **lenses** the product uses to answer the questions below.

**North star:** automated **weekly / monthly Digests** per product (`kih` · `lindle` · `yca`) — top metrics from BigQuery, delivered to **Slack and/or email**. Decide/Prove UIs are for drill-down when a Digest flags something.

**Product vehicle — one monorepo:**

| Decision | Repo | Action |
| --- | --- | --- |
| **HOLD** | `stateboard` → **`insights`** | Monorepo (Decide + Narrate + Prove) |
| **REMOVE** | `Aureyo` | → `insights/apps/decide`, then delete |
| **REMOVE** | `Raporting` | → `insights/apps/narrate`, then delete |

| App | Path | Role |
| --- | --- | --- |
| **Decide** | `apps/decide` | On-demand UI |
| **Narrate** | `apps/narrate` | Digest engine + Slack/email |
| **Prove** | Prove.Api + `apps/prove` | Cost, map, health |

```
   Cloud Scheduler (weekly / monthly)
              │  for each product: kih, lindle, yca
              ▼
        BQ Snapshot ──► Narrate ──► Digest (Slack + email)
              ▲              │
              │              └─ optional: save + link in Decide
         cognispace
   GA4 · Billing · Langfuse · app facts

   Decide = on-demand / history     Prove = cost · map · health
   git: single repo `insights` (ex stateboard)
```

**Positioning:** Digests are the default delivery; UIs are secondary. Infra cost/health is a **reality check** inside Digests, not a separate product hero.

**Nomenclature + subplans**

- [[01 Initiatives/Synthapse/Insights — Nomenclature]] — monorepo + codes (`kih`/`lindle`/`yca`), Snapshot, BQ  
- [[01 Initiatives/Synthapse/Insights — Subplan Decide]] — `apps/decide`  
- [[01 Initiatives/Synthapse/Insights — Subplan Narrate]] — `apps/narrate`  
- [[01 Initiatives/Synthapse/Insights — Subplan Prove]] — Prove API + web  

## Lenses (mental model)

| Lens | Tool | Answers |
| --- | --- | --- |
| **What users did** | GA4 / GTM | Traffic, sessions, funnels, acquisition, client events |
| **How they experienced UI** | **Contentsquare** (Clarity = legacy IDs only) | Session UX, friction; recordings/heat where CS provides |
| **What LLM/RAG did** | **Langfuse** | Traces, generations, latency, cost/tokens, RAG, scores |
| **What actually happened** | GCP app data | Users, orgs, subscriptions, orders, feature use |
| **What infra / cloud cost** | **GCP Billing** → BQ hub `cognispace` | Detailed $ by project/service/SKU/label |
| **Are services healthy?** | Healthchecks + exceptions | Per-service up/down + exception evidence (**Grafana postponed**) |

```
                 Product Intelligence
                         │
     ┌───────────┬───────┼───────┬───────────┬────────────┐
     │           │       │       │           │            │
 Quantitative  UI qual  LLM/RAG  Business   FinOps    Reliability
     │           │       │       │           │            │
    GA4       Clarity  Langfuse  App DB   Billing   Health+exceptions
```

**Already in play:** Dr Kiwi (Gemini + Langfuse), Lindle agents (Langfuse in metrics), YCA (Langfuse traces).

**Do not** build the warehouse *around* GA4 alone. App/GCP + Langfuse + **Billing export** are equally important. Don’t infer “what did Cloud Run / SQL / Gemini API cost?” from Monitoring alone — use **Billing → BigQuery** for line-item cost; use Langfuse for LLM token economics; join both in `marts.cost`.

**Out of scope (near term):** GKE for apps, self-hosted Prometheus farm, Segment/Amplitude, copying every Clarity recording into BQ, replacing Langfuse UI with only BQ (keep Langfuse for trace drill-down).

---

## Target architecture

```
                         DATA SOURCES
                              │
   ┌─────────┬─────────┬──────┼──────┬─────────┬──────────┐
   │         │         │      │      │         │          │
   ▼         ▼         ▼      ▼      ▼         ▼          ▼
  GA4     Clarity   Langfuse  App   GCP     GCP Billing  …
 traffic    UX       LLM/RAG  DB   metrics   (FinOps)
   │         │         │      │      │         │
   └─────────┴─────────┴──────┼──────┴─────────┘
                              ▼
                         ┌───────────┐
                         │ BigQuery  │  ← source of truth
                         │ raw → stg → core → marts
                         └─────┬─────┘
                               │  dbt or Dataform
                ┌──────────────┼───────────────┐
                ▼              ▼               ▼
           BI / Analytics   Grafana      Langfuse UI
           Looker Studio    health+AI    trace drill-down
           + AI + cloud $   cost alerts
```

### Three visualization layers

| Layer | Tool | Use for |
| --- | --- | --- |
| **BI / Analytics** | Looker Studio (→ Looker later) | Cohorts, retention, revenue, funnels, **AI cost**, **GCP detailed billing**, exec |
| **Operational** | Grafana (+ BQ + Monitoring) | **Service healthboard**, exceptions, infra, **LLM + cloud $ burn**, budgets, deploy annotations, alerts |
| **LLM debug** | **Langfuse UI** | Single-trace inspection — don’t replace with BQ |

Grafana/Looker: “is AI + cloud healthy / expensive / adopted?”  
**Grafana healthboard:** “is every service up — and what exceptions fired?”  
Langfuse: “what went wrong in *this* chat?”  
Billing export: “which SKU / project / label spent the money?”

---

## Products in scope

> Inventory updated **2026-09-13**. Secrets in env only.  
> **BQ hub:** `cognispace` (all GA4 / Billing / Langfuse aggregates land here when wired).  
> **UX SoT:** **Contentsquare** (Clarity IDs kept as legacy info only).  
> **Grafana:** postponed.

| Product | GA4 | UX | Langfuse (EU) | GCP | Billing | App DB |
| --- | --- | --- | --- | --- | --- | --- |
| **YCA / CzatBudowlany** | Property **`494547928`** · Measurement `G-DZNYJF6HSB` · Stream `11400440203` · Account TBD | **Contentsquare** (primary) · Clarity legacy `t9jhgsv5zv` · Hotjar `6502269` | **`yca-ca-mvp`** | `adroit-router-462912-n6` (#729811640717) | `01F545-2E8963-C6EBE1` | Cloud SQL `ycadb` |
| **Lindle** | Account **`369357278`** · Property **`506154105`** · Measurement **`G-71BSGEPP21`** (Firebase `G-R8MG7V24XD` secondary) | **Contentsquare** (primary) · Clarity legacy `tfa09ihgyu` | Project **Lindle** `cmei38jmn00s1ad07oqzvyqcz` · Org Synthapse `cmehh1da7003nad07axuh0p6a` | `cognispace` (#946555989276) · `europe-central2` | `01C7B7-5B77CD-27EDAD` | Firestore · Neo4j Aura |
| **Dr Kiwi / KIH** | Property **`499549002`** · Measurement `G-CBTHK8QQ6N` · GTM `GTM-KGZ332RB` | **Contentsquare** `57dec74d2513b` (primary) · Clarity — none | Project **DrKiwi** `cmph5si3406aoad0e8o2j8p4d` · Org Keep It Healthy `cmph5sdsp06ajad0e9vldfnn7` | `dr-kiwi-app` · `europe-central2` | `01BF64-6A600F-517AFE` | Cloud SQL `dr-kiwi-app-database` |

Labels: `product=czatbudowlany|lindle|kih` · `env=prod|staging`.

### Phase 0 status

| Item | Status |
| --- | --- |
| Product / GA4 / Langfuse / GCP / billing IDs | ✅ largely filled |
| BQ hub = `cognispace` | ✅ decided |
| UX = Contentsquare (Clarity legacy noted) | ✅ decided |
| Grafana | ⏸ postponed |
| Service inventory + `/health` | ✅ captured 2026-09-13 (see inventory below; health URLs still to confirm) |
| Questions shortlist | ✅ shared set below |
| Billing export → `cognispace` BQ | ⬜ Phase 1/4c |
| Consent/PHI note (KIH) | ⬜ short note |

### How to generate the service list (include jobs & async)

Inventory is **not only Cloud Run HTTP services**. Include anything that can fail, cost money, or affect product health:

| Kind | Examples (esp. Dr Kiwi) | How to discover |
| --- | --- | --- |
| **HTTP services** | API, web, admin | `gcloud run services list` |
| **Cloud Run jobs** | batch / one-shot | `gcloud run jobs list` |
| **Cloud Tasks queues** | notifications, CMS reindex, audience notify | `gcloud tasks queues list --location=REGION` |
| **Schedulers** | cron → Task/Job/HTTP | `gcloud scheduler jobs list --location=REGION` |
| **In-service jobs** | Celery/RQ/Django-Q, management commands, workers inside a Run service | From **code/docs** (e.g. Dr Kiwi Current State “Jobs”) — not always visible as GCP resources |
| **Other async** | Pub/Sub push, Eventarc, Cloud Functions, Workflows | list per product project as needed |
| **Data** | Cloud SQL, Redis, Neo4j | one row each as **dependency** (health via `/health` checks or Monitoring) |

### One-shot commands (copy-paste)

List **services + jobs + task queues + schedulers** for each project:

```bash
list_gcp_workloads () {
  local PROJECT="$1"
  local REGION="${2:-europe-central2}"
  echo "========== PROJECT=$PROJECT REGION=$REGION =========="

  echo "--- Cloud Run services ---"
  gcloud run services list --project="$PROJECT" --region="$REGION" \
    --format='table(metadata.name,status.url,status.conditions[0].status)' 2>/dev/null \
    || gcloud run services list --project="$PROJECT" \
         --format='table(metadata.name,region,status.url)'

  echo "--- Cloud Run jobs ---"
  gcloud run jobs list --project="$PROJECT" --region="$REGION" \
    --format='table(metadata.name,status.latestCreatedExecution.completionTimestamp)' 2>/dev/null \
    || echo "(none or API not enabled)"

  echo "--- Cloud Tasks queues ---"
  gcloud tasks queues list --project="$PROJECT" --location="$REGION" \
    --format='table(name.basename(),state)' 2>/dev/null \
    || echo "(none or API not enabled)"

  echo "--- Cloud Scheduler ---"
  gcloud scheduler jobs list --project="$PROJECT" --location="$REGION" \
    --format='table(name.basename(),schedule,state)' 2>/dev/null \
    || echo "(none or API not enabled)"

  echo "--- Cloud Functions (gen2 if any) ---"
  gcloud functions list --project="$PROJECT" --regions="$REGION" \
    --format='table(name,state,url)' 2>/dev/null \
    || echo "(none or API not enabled)"

  echo
}

list_gcp_workloads cognispace europe-central2
list_gcp_workloads dr-kiwi-app europe-central2
list_gcp_workloads adroit-router-462912-n6 us-central1   # YCA SQL was us-central1; also try europe-central2 if empty
list_gcp_workloads adroit-router-462912-n6 europe-central2
```

### Service inventory (captured 2026-09-13)

**Scope for Product Intelligence (in):** KIH · Lindle · YCA.  
**Out (cognispace portfolio noise):** bolt, daas, mas, math, sport, stateboard, videoanalyzer, grafana — track for billing only if needed, not healthboard v1.

#### Dr Kiwi — `dr-kiwi-app` / `europe-central2`

| name | kind | signal | notes |
| --- | --- | --- | --- |
| `dr-kiwi-app` | cloud_run_service | URL + `/health` ⬜ | https://dr-kiwi-app-rocn5g3qfq-lm.a.run.app · STATUS True |
| `notification-queue-v2` | cloud_tasks_queue | depth / age / errors | RUNNING |
| `cds-process-due-notifications` | run_job + scheduler `*/15 * * * *` | last execution | OK 2026-09-13 |
| `cds-purge-events` | run_job + scheduler `45 3 * * 0` | last execution | ⚠ **FAILED** 2026-09-13 01:45 |
| `cds-schedule-reengage` | run_job + scheduler `0 9 * * *` | last execution | OK |
| `cds-schedule-supplement-missed` | run_job + scheduler `0 4 * * *` | last execution | OK |
| `cds-send-daily-digest` | run_job + scheduler `0 7 * * *` | last execution | OK |
| `cds-send-engagement-lifecycle-emails` | run_job + scheduler `0 8 * * *` | last execution | OK |
| `cds-snapshot-health-score` | run_job + scheduler `15 4 * * *` | last execution | job listed; no latest execution in dump |
| `cds-sync-community-challenge-reminders` | run_job + scheduler `0 2 * * *` | last execution | OK |
| `cds-sync-supplementation-reminders` | run_job + scheduler `0 2 * * *` | last execution | OK |
| `cds-finalize-streak-day` | scheduler only `30 3 * * *` | target health | ENABLED — confirm target job/HTTP |
| `weekly-stats-slack` | scheduler `0 17 * * 5` | target health | ENABLED |
| `index-rag` | run_job (ops) | last execution | OK 2026-09-10 — RAG index |
| `migrate-collectstatic` | run_job (ops) | last execution | deploy utility |
| `create-superuser` / `seed-catalog*` / `fix-survey-raw-labels` | run_job (ops/one-off) | — | low priority for healthboard |
| `addFcmToken` / `addUser` / `deleteUser` / `sendScheduledPushNotifications` | cloud_function | errors / invocations | legacy? confirm still used vs Tasks |

**KIH alert priority:** Run service · `notification-queue-v2` · all `cds-*` scheduled jobs · **fix `cds-purge-events`**.

#### Lindle — `cognispace` / `europe-central2` (+ duplicate on adroit-router)

| name | kind | signal | notes |
| --- | --- | --- | --- |
| `lindle-backend` | cloud_run_service | URL + `/health` ⬜ | cognispace URL · also on `adroit-router` europe-central2 |
| `lindle-backend-agents` | cloud_run_service | URL + `/health` ⬜ | agents |
| `procureiq` | cloud_run_service | URL + `/health` ⬜ | related procurement stack |

No Cloud Tasks / Scheduler in cognispace (API not enabled / empty).

#### YCA / CzatBudowlany — `adroit-router-462912-n6` / `europe-central2`

| name | kind | signal | notes |
| --- | --- | --- | --- |
| `yca-ca-backend` | cloud_run_service | URL + `/health` ⬜ | |
| `yca-ca-backend-2` | cloud_run_service | URL + `/health` ⬜ | confirm which is prod SoT |
| `yca-ca-auth` | cloud_run_service | URL + `/health` ⬜ | |
| `yca-ca-backend-payment` | cloud_run_service | URL + `/health` ⬜ | |
| `yca-ca-backend-payment-testing` | cloud_run_service | — | testing — lower priority |
| `yca-ca-backend-testing` | cloud_run_service | — | testing |
| `yca-car-backend` | cloud_run_service | URL + `/health` ⬜ | confirm product role |
| `langfuse-migration` | run_job (`us-central1`) | last execution | one-off / ops |

#### Cognispace — other (out of PI v1 healthboard)

`bolt-backend` · `cognispace` · `daas-backend` · `grafana-service` · `mas-backend` · `math-backend` · `sport-backend` · `stateboard-api` · `videoanalyzer-microservice` — optional billing attribution later.

#### Next on this inventory

- [ ] Confirm `/health` (or `/ready`) on each **in** Run service  
- [ ] Investigate **`cds-purge-events` FAILED**  
- [ ] Confirm KIH Cloud Functions still live vs replaced by Run jobs/Tasks  
- [ ] Pick YCA prod SoT between `yca-ca-backend` vs `yca-ca-backend-2`  
- [ ] Clarify Lindle: cognispace vs adroit-router `lindle-backend` (which is prod)

**Not listed by gcloud (add by hand from code/docs):** in-service handlers behind `notification-queue-v2`, other Django task names.

**Rules**
- One row per **failure domain** (queue, job, worker), not only public URLs.  
- Health for queues/jobs ≠ `/health`: queue depth, task age, execution success, Error Reporting.  
- Grafana postponed → still use this table for Monitoring alerts later.

### Security

Do not commit Langfuse **secret** keys, DB passwords, Neo4j creds. Public `G-*` / project IDs / Langfuse project ids OK in this inventory.

---

## Warehouse design (BigQuery layers)

```
BigQuery
│
├── raw
│   ├── ga4          # native daily export (nested event_params)
│   ├── clarity      # sparse: API aggregates / links only
│   ├── langfuse     # traces, observations, scores, costs (export/API)
│   ├── app          # users, orgs, subs, orders, app events
│   ├── gcp          # Monitoring / Logging / uptime / Error Reporting exports
│   ├── billing      # GCP Billing export (detailed usage + cost)
│   └── health       # optional curated healthcheck + exception events
│
├── staging
│   ├── stg_ga4_events
│   ├── stg_langfuse_traces
│   ├── stg_langfuse_observations
│   ├── stg_langfuse_scores
│   ├── stg_gcp_billing
│   ├── stg_service_health       # probe results per service
│   ├── stg_exceptions           # app/platform exceptions (normalized)
│   ├── stg_users
│   ├── stg_accounts
│   └── stg_orders
│
├── core
│   ├── dim_user
│   ├── dim_account
│   ├── dim_product
│   ├── dim_feature
│   ├── dim_prompt / dim_model
│   ├── dim_gcp_service
│   ├── dim_service              # logical service: api, web, workers, …
│   ├── fct_events
│   ├── fct_sessions
│   ├── fct_llm_traces
│   ├── fct_llm_generations
│   ├── fct_rag_retrievals
│   ├── fct_gcp_cost
│   ├── fct_healthchecks         # timestamp × service × status × latency_ms
│   ├── fct_exceptions           # timestamp × service × type × count / sample
│   ├── fct_orders
│   └── fct_subscriptions
│
└── marts
    ├── product
    ├── ai
    ├── cost
    ├── reliability              # uptime, health, exception rates
    ├── marketing
    ├── revenue
    ├── customer
    └── executive
```

**Rule:** don’t expose raw GA4 (`UNNEST(event_params)`, `_TABLE_SUFFIX`) to everyone — publish clean `fct_events` / marts. Same for Langfuse and Billing: analysts use `marts.ai` / `marts.cost`, not raw export tables.

### App / GCP entities to ingest (examples)

`users` · `accounts/organizations` · `subscriptions` · `plans` · `products` · `features` · `orders` · `payments` · `experiments` · `support interactions` · `application events` · `API usage` · `errors` · `performance` · `feature flags`

### GA4 contributes

page views · sessions · acquisition · campaigns · device/browser · conversion events · product interactions · funnels · attribution (user/session/event scope for joins)

### Paths into BQ

```
Cloud SQL ──scheduled query / Datastream──► raw.app
App events ──Pub/Sub (optional)──────────► raw.app
Cloud Monitoring / Logging ──export──────► raw.gcp
GA4 ──native BigQuery link───────────────► raw.ga4  (hub: cognispace)
Contentsquare ── qualitative / deep-link──► (not full warehouse; optional later)
Clarity ── legacy only ───────────────────► keep IDs; do not build on it
Langfuse ──API / export / webhook ETL───► raw.langfuse
GCP Billing ──Billing export to BQ──────► raw.billing   ★ detailed $ → cognispace
```

**Langfuse ingest options (pick one later):** scheduled pull via API → BQ; Langfuse native export if available on your plan; app writes mirror metrics to BQ only for aggregates (prefer Langfuse as system of record for traces).

---

## GCP Billing — detailed cost (FinOps lens)

**Goal:** every GCP subscription / usage line (Cloud Run, Cloud SQL, Artifact Registry, Networking, Gemini/Vertex, Grafana host project, etc.) lands in BigQuery with enough detail to attribute cost **per product**.

### Enable (once per billing account)

1. Cloud Billing → **Billing export** → BigQuery  
2. Prefer **Detailed usage cost** export (SKU-level), not only standard summary  
3. Dataset in hub project, e.g. `raw_billing` / `gcp_billing_export`  
4. Optional: **Pricing export** for list vs effective rates  

### Required labels (enforce on resources)

| Label | Example | Why |
| --- | --- | --- |
| `product` | `lindle` / `kih` / `czatbudowlany` | Split shared billing account |
| `env` | `prod` / `staging` | Don’t mix pilot vs prod cost |
| `service` | `api` / `web` / `workers` | Optional drill-down |

Without labels, cost stays at **project** grain only — still useful, weaker product marts.

### What “detailed cost” means in the warehouse

| Field (from Billing export) | Use |
| --- | --- |
| `project.id` / `project.name` | Which GCP project |
| `service.description` | Cloud Run, SQL, … |
| `sku.description` | Exact SKU / subscription line |
| `usage.amount` + unit | Quantity |
| `cost` + `currency` | $ amount |
| `invoice.month` / `usage_start_time` | Time grain |
| `labels` | product / env attribution |
| `credits` | Promos, CUD, sustained use |

### Cost mart sketch (`marts.cost`)

| Grain | Metrics |
| --- | --- |
| day × product × env | total_cost_usd, by top services |
| day × product × service | Cloud Run / SQL / Networking / … |
| day × product × sku | subscription & usage line detail |
| month × product | invoice-aligned total + MoM Δ |
| day × product | **cloud_cost** + **langfuse_llm_cost** = **cogs_infra_ai** |

### Correlate (product intelligence)

```
sessions / conversion (GA4)
        ×
cloud $ (Billing) + LLM $ (Langfuse)
        ×
errors / latency (Monitoring)
```

Answer: “Did we spend more and convert less?” / “Which product burns cash idle?”

### Grafana / Looker

- Looker page **Cloud cost**: by product, service, SKU, month  
- Grafana: daily burn + budget alerts (Billing data via BQ datasource or Cloud Monitoring billing metrics)  
- Keep **Cloud Billing console** for invoice disputes; warehouse for product narrative

---

## Service healthchecks + exceptions (Reliability lens)

**Goal:** for **every** deployable service (per product), always see: is it healthy? If not, **what exceptions** occurred?

### Service inventory (fill in Phase 0)

| Product | Service | Health endpoint / probe | Where it runs |
| --- | --- | --- | --- |
| KIH | API | `/health` (or `/ready`) | Cloud Run |
| KIH | Web / patient app | HTTP uptime check | Hosting / Run |
| KIH | Cloud Tasks queues + in-service jobs | queue depth / age / last success / errors | Tasks + workers (see service list) |
| Lindle | API | `/health` | Cloud Run |
| Lindle | Agents / workers / jobs | `/health`, job success, or queue signals | Run / Jobs / Tasks |
| CzatBudowlany | API / web + async jobs | `/health` + job/queue signals | Cloud Run (+ Tasks/Jobs if any) |
| Shared | Grafana | postponed | — |

Every row must appear on the **Grafana healthboard** (green/red + last check time).

### What to collect

| Signal | Source | Show |
| --- | --- | --- |
| **Healthcheck** | App `/health` + **Cloud Monitoring uptime checks** (and/or Cloud Run revision ready) | status OK/FAIL, latency_ms, region |
| **Platform liveness** | Cloud Run `request_count`, instance count, 5xx | service up but degraded |
| **Exceptions** | Cloud Error Reporting, Cloud Logging (`severity>=ERROR`), app structured `exception` events | type, message fingerprint, count, last_seen, sample link |
| **Dependency health** (optional) | `/health` details: DB, Redis, Langfuse, external APIs | which dependency failed |

### Healthcheck contract (app)

Each service exposes a cheap probe, e.g.:

- `GET /health` → `200` + `{ "status": "ok", "service": "kih-api", "checks": { "db": "ok" } }`  
- Failures → non-2xx; dependency failures listed in `checks`  
- No auth required for probe (or dedicated uptime token)

### Exceptions when they occur

When health fails **or** error rate spikes:

1. **Alert** (Pager/Slack/email) with service + product label  
2. **Grafana** panel: exception rate + top fingerprints next to the red health cell  
3. **BQ** `fct_exceptions` row(s) for later join: “conversion ↓ same hour as exception burst”  
4. Link out to Logging / Error Reporting (and Langfuse if AI path)

Do **not** only show “service down” — always pair with **exception evidence** when available.

### Reliability mart sketch (`marts.reliability`)

| Grain | Metrics |
| --- | --- |
| day × product × service | uptime_%, checks_failed, p95_health_latency |
| hour × product × service | exception_count, top_exception_types |
| incident | start/end, service, trigger (health vs 5xx vs burn) |

### Grafana healthboard (required)

One board (or folder per product) with:

```
Product │ Service      │ Health │ Last check │ Exceptions (1h) │ p95 latency
--------│--------------│--------│------------│-----------------│------------
KIH     │ api          │ 🟢/🔴  │ …          │ N / top type    │ …
KIH     │ web          │ 🟢/🔴  │ …          │ …               │ …
Lindle  │ api          │ …      │ …          │ …               │ …
…
```

Alert rules: health FAIL, exception surge, 5xx surge — per service.

---

## Unified identity (highest leverage)

Goal: one story across tools.

```
              canonical_user_id
                     │
     ┌───────┬───────┼───────┬──────────┐
     │       │       │       │          │
  ga4_id  clarity  app_id  langfuse   session_id
                     │    metadata     (app + GA4)
                     │    userId /
                     │    sessionId
```

**`dim_user` (sketch)**

| Column | Notes |
| --- | --- |
| `canonical_user_id` | Stable warehouse key |
| `app_user_id` | System of record when logged in |
| `account_id` | Org / tenant |
| `ga4_user_id` / `user_pseudo_id` | From GA4 export |
| `clarity_user_id` | Only if consent allows join |
| `created_at`, `signup_date`, `plan`, `country`, `customer_status` | From app |

**Langfuse tagging (required for joins)** — set on every trace:

| Metadata | Purpose |
| --- | --- |
| `user_id` | = `app_user_id` when authenticated |
| `session_id` | chat / agent session (align with app) |
| `account_id` / `tenant_id` | multi-tenant |
| `product` | `lindle` \| `kih` \| `czatbudowlany` |
| `feature` | e.g. `rag_chat`, `negotiation_agent` |
| `environment` | `prod` / `staging` |

Join only what **consent / privacy** allows (EEA/UK Clarity; don’t put PHI/PII into Langfuse prompts beyond policy). Don’t blindly stitch IDs.

Answer you want later:  
*“Came from Google Ads → pricing → signed up → opened AI chat → 3 RAG turns ($0.04) → low score → churned.”*

---

## Canonical product event taxonomy

Don’t let every surface invent random event names. Standardize:

**Event names (examples)**  
`user_signed_up` · `user_logged_in` · `onboarding_started` · `onboarding_completed` · `feature_viewed` · `feature_started` · `feature_completed` · `feature_failed` · `project_created` · `project_updated` · `project_deleted` · `subscription_started` · `subscription_upgraded` · `subscription_cancelled` · **`ai_chat_started`** · **`ai_message_sent`** · **`rag_query`** · **`agent_run_started`** · **`agent_run_completed`** · **`agent_run_failed`**

**Standard properties**  
`event_id` · `event_timestamp` · `canonical_user_id` · `account_id` · `session_id` · `product_id` · `feature_id` · `experiment_id` · `platform` · `device` · `country` · `properties` (JSON) · **`langfuse_trace_id`** (when AI)

Emit from **app backend** when truth matters; use GA4 for client journey; **Langfuse for LLM spans**; map product events into `fct_events` and AI into `fct_llm_*`.

---

## Product intelligence marts (differentiate from “GA4 clone”)

| Mart | Example metrics |
| --- | --- |
| **Adoption** | users_exposed, started, completed, activation_rate, WAU/MAU |
| **Engagement** | DAU/WAU/MAU, actions_per_user, completion_rate, failure_rate |
| **Retention** | cohort × week_0…week_12 |
| **Conversion** | landing → signup → activation → trial → paid → retained |
| **Customer health** | active_users, feature_adoption, errors, support, MRR, health_score |
| **Funnel** | Signup → Onboarding → First project → First success → Second session → Invite → Paid → Retained |
| **AI / LLM** | traces, msgs/user, tokens, **$ cost**, p95 latency, error rate, RAG hit rate, score/feedback, cost per paid account |
| **Cloud cost** | GCP **detailed** $ by product/service/SKU; subscriptions; MoM; idle vs traffic; cloud+AI COGS vs revenue |
| **Reliability** | Per-service **healthcheck** status; uptime %; **exceptions** (count, type) when unhealthy or erroring |

### AI mart sketch (`marts.ai`)

| Grain | Metrics |
| --- | --- |
| day × product × feature × model | traces, generations, input/output tokens, cost_usd, p50/p95 latency, error_count |
| day × account | AI active, cost, msgs, avg score |
| day × prompt/version | usage, cost, score (for prompt deploys) |

Trace path when something breaks:  
**business metric → segment → feature → GA4 → Clarity (UI) → Langfuse (LLM/RAG) → health/exceptions → Billing spike → deploy**

---

## Where Contentsquare fits (Clarity = legacy)

**Contentsquare** = qualitative / UX layer (primary).  
Clarity project IDs kept in inventory only — **do not build** new Clarity integrations.

- Quant in BQ/GA4: “Feature X conv 42%…”  
- Qual in Contentsquare: friction on that path  

Runbook: anomaly in Looker/GA4 → open Contentsquare for that URL/flow.

---

## Where Langfuse fits

Langfuse = **LLM/RAG observability + cost**, system of record for traces.

| Keep in Langfuse UI | Push to BigQuery |
| --- | --- |
| Full prompt/completion payloads (debug) | Aggregates: tokens, cost, latency, errors |
| Span tree / RAG retrieve details | Trace-level facts for joins (`trace_id`, user, session) |
| Manual scores / eval runs | Daily cost & quality marts |
| Prompt version comparison | Prompt version as dimension in marts |

**Standards for every AI feature**

1. Create Langfuse trace per user-visible AI action (chat turn, agent run)  
2. Nest generations + retrieve spans (RAG) under that trace  
3. Tag `user_id`, `session_id`, `account_id`, `product`, `feature`  
4. Record scores (thumbs, eval, hallucination flags) when available  
5. Link app event with `langfuse_trace_id` for BQ joins  

**Don’t:** dump full prompt text with PHI into BQ by default; store IDs + aggregates in BQ, drill in Langfuse under access control.

**Cost / product questions Langfuse unlocks**

- Cost per tenant / per feature / per model  
- RAG vs non-RAG latency and failure  
- Correlation: AI errors ↑ → support tickets / churn  
- Agent pack consumption vs pricing (Lindle)

---

## Transformation & stack

| Layer | Recommendation |
| --- | --- |
| Event collection | GA4 + GTM + **application events** |
| UX | **Contentsquare** (Clarity = legacy) |
| LLM / RAG | **Langfuse** (traces, cost, scores) |
| App data | Cloud SQL / Firestore / Neo4j → BQ as needed |
| Warehouse hub | **BigQuery in `cognispace`** |
| Billing / FinOps | **GCP Billing export → cognispace BQ** |
| Transform | **dbt** (or Dataform) |
| BI | Looker Studio → Looker if scale |
| Ops dashboards | **Grafana postponed** — use Cloud Monitoring meantime |
| LLM debug | **Langfuse UI** |

```
raw → staging → intermediate → core → marts
         (dbt incremental where needed)
```

---

## Start from questions (same core for every product)

Ask these **for each** of YCA / Lindle / Dr Kiwi (answer will differ by product).

### A. Product & growth (all three)

1. How many users are actually active (DAU/WAU/MAU)?  
2. Where do users abandon onboarding / first value?  
3. Which acquisition channels produce *retained* users (not just visits)?  
4. Time from signup → activation?  
5. What does “activated” mean for this product — and what % hit it?

### B. UX (Contentsquare — all three)

6. Which pages/flows have the worst friction (rage/dead clicks, drop-offs)?  
7. When conversion dips, what does Contentsquare show on that path?

### C. AI / Langfuse (all three that have LF)

8. AI cost per day / per feature (and per account if tagged)?  
9. Latency p95 and error rate of AI paths?  
10. Does AI failure/cost correlate with churn or support load?

### D. Cloud cost (Billing → cognispace)

11. GCP $ per day/month for this product’s project(s)?  
12. Which services/SKUs dominate the bill?  
13. Cloud + LLM COGS vs active users (or revenue if known)?

### E. Reliability (list now; Grafana later)

14. Is every listed service healthy?  
15. When something fails, what exceptions appear?  
16. Uptime % this week by service?

### Product-specific add-ons

| Product | Extra questions |
| --- | --- |
| **YCA / CzatBudowlany** | Which construction tools/features are used vs ignored? Chat/RAG quality vs cost? |
| **Lindle** | Coverage/gap insights: do users act on the “vital few”? Agent pack consumption vs pricing? Paul-scale: can we show 65k → top N impact? |
| **Dr Kiwi** | Booking / care-plan funnels? PHI-safe: what must *not* land in BQ from Langfuse? Consent for UX ↔ app joins? |

Design warehouse **and product UI** backwards from A–E + add-ons — each screen/widget should answer one question, not “show all data”.

---

## Fusion plan — Decide + Narrate + Prove

### Principle

**One monorepo, three apps.** HOLD `stateboard` → `insights`; REMOVE Aureyo + Raporting after import. Digests primary; UIs secondary. Shared `cognispace` BQ.

| Mode | Primary surface | Backend | Answers |
| --- | --- | --- | --- |
| **Digest** | Slack / email | Narrate (`apps/narrate`) | Vital-few A–E |
| **Decide** | `apps/decide` | Narrate + Snapshot | On-demand A–C |
| **Prove** | `apps/prove` + Prove.Api | Billing / inventory / health | Drill-down D–E |

**Narrate** is the Digest engine (not a third user-facing app).

### How to proceed (sequence)

**Step 0 — Monorepo (done as decision)**  
HOLD **`insights`** (ex stateboard). REMOVE Aureyo + Raporting after `apps/decide` + `apps/narrate` land. See [[Insights — Nomenclature]].

**Step 1 — Shared truth (this is the spine)** — Phase 1 of warehouse  
- GA4 → BQ in **`cognispace`** (one product first)  
- Billing export → `cognispace`  
- Without this, Digests stay “vibes” and Prove cost stays “TF estimate only”

**Step 2 — Wire Narrate Digests to real metrics**  
- Input: Snapshot from BQ (sessions, activation, friction, AI $, cloud $, health flags)  
- Output: Digest → Slack/email; optional save in Decide  
- Scheduler: weekly + monthly × 3 products

**Step 3 — Prove tab**  
- Keep hex/TF map as differentiator  
- Add: product switcher (kih / lindle / yca) · cloud $ from Billing · health from service inventory (jobs/queues)  
- Link from Digest when cost/health is red

**Step 4 — Soft UX fusion**  
Shared nav Decide ↔ Prove inside monorepo deploys; Digests remain the default “open” path (inbox).

**Step 5 — Finish repo cleanup**  
- Snapshot contract stable  
- Narrate + Decide imported and deployed from `insights`  
- Archive/delete Aureyo + Raporting

### What each question uses

| Questions | Decide (Aureyo/Raporting) | Prove (Stateboard) |
| --- | --- | --- |
| A Growth 1–5 | GA4 + app facts → Raporting narrative | optional KPI strip |
| B UX 6–7 | Contentsquare → “fix here” in report | — |
| C AI 8–10 | Langfuse aggregates → cost/quality in report | AI burn sparkline optional |
| D Cost 11–13 | “bill vs users” in narrative | **Billing detail + SKUs** |
| E Reliability 14–16 | “outage affected conversion” if joined | **healthboard jobs/queues** |

### Anti-goals

- New fourth frontend repo  
- Big-bang monorepo merge  
- Raporting as standalone SaaS again  
- Stateboard-only story (infra without business decisions)  
- Aureyo-only story (marketing copy without BQ/Billing truth)

### Near-term “done”

1. BQ hub live with ≥1 GA4 property + Billing  
2. One Aureyo/Raporting report fed by **real** metrics JSON  
3. Stateboard page: one product’s cloud $ + service list status  
4. Cross-link Decide ↔ Prove in UI or bookmarks

---

## Technical proceed — repos & architecture

### Decision: **one monorepo** (`insights`)

| | Repo | Action |
| --- | --- | --- |
| **HOLD** | `stateboard` → rename **`insights`** | Base tree (Api + web + packages already) |
| **REMOVE** | `Aureyo` | Import → `apps/decide`, then archive/delete |
| **REMOVE** | `Raporting` | Import → `apps/narrate`, then archive/delete |

Languages stay mixed (.NET / Python / TS) — **one git tree**, still **separate deployables** (Cloud Run services). Shared: `InsightsSnapshot`, BQ, CI, cognispace.

| Path | Deploy (cognispace) | Owns |
| --- | --- | --- |
| Prove.Api (+ `apps/prove`) | `prove-api` (today `stateboard-api`) + web | TF graph, cost/health APIs |
| `apps/narrate` | `narrate` | Digest + `POST /v1/insights/report` |
| `apps/decide` | frontend hosting | On-demand UI |

**Merge sequence:** (1) rename `stateboard` → `insights` (2) copy Narrate in, wire Digest (3) copy Decide in (4) delete Aureyo + Raporting remotes when green.

### Target runtime architecture

```
Browser
  ├─ Decide ──HTTP──► Narrate API ──► LLM + PDF/GCS + Slack/email
  │     │                  ▲
  │     │                  │ InsightsSnapshot (JSON)
  │     └──────────┐       │
  │                ▼       │
  │          BigQuery (cognispace)
  │          datasets: raw_* / marts_*
  │                ▲
  │                │
  └─ Prove web ─HTTP─► Prove.Api ──┘
                           ├─ TF scan / pricebook
                           └─ marts.cost / marts.reliability

ETL / config (no user traffic):
  GA4 export ───────────────► BQ cognispace
  Billing export ───────────► BQ cognispace
  Langfuse ETL (later) ─────► BQ cognispace
  gcloud inventory (jobs) ──► config YAML or BQ dim_service

git: insights/  (monorepo)
  apps/decide · apps/narrate · apps/prove · Prove.Api · packages/
```

**No shared OLTP DB** between apps except **BigQuery** (+ optional Firebase/GCS for Digest archive).

### Shared contract (the fusion glue)

One versioned JSON DTO both sides understand, e.g. `InsightsSnapshot` v1:

```json
{
  "product": "kih|lindle|czatbudowlany",
  "period": { "from": "2026-09-01", "to": "2026-09-13" },
  "growth": { "dau": 0, "wau": 0, "activation_rate": 0, "top_channels": [] },
  "ux": { "top_friction_urls": [], "notes": "" },
  "ai": { "cost_usd": 0, "error_rate": 0, "p95_ms": 0 },
  "cloud": { "cost_usd": 0, "top_skus": [] },
  "reliability": { "services_up": 0, "services_total": 0, "failing": [] }
}
```

| Producer | Consumer |
| --- | --- |
| **BQ scheduled query / thin Insights Query API** builds DTO | Aureyo (show KPIs) · Raporting (prompt context) · Stateboard (Prove panels) |

v1 implementation options (pick simplest):

1. **Scheduled query → BQ table `marts.insights_snapshot_daily`** · each app reads with BQ client (SA)  
2. **Thin `insights-query` Cloud Function/Run** — `GET /v1/snapshot?product=kih` runs SQL, returns DTO (better if you don’t want BQ keys in browsers)

Recommend **2 for browser**, **1 for Raporting server**.

### Repo-by-repo technical work

#### 1) `cognispace` BQ (spine — do first)

```
cognispace /
  raw_ga4_*          ← GA4 linked exports (per property or consolidated)
  raw_billing        ← Billing export
  marts_growth       ← views from GA4
  marts_cost         ← from billing + labels
  marts_reliability  ← later from Monitoring / inventory
  marts_insights_snapshot_daily
```

- IAM: Stateboard SA + Raporting SA = `bigquery.dataViewer` (+ jobUser) on those datasets  
- Labels on GCP resources: `product`, `env`

#### 2) `Raporting` (Python FastAPI)

- Add endpoint e.g. `POST /v1/insights/report`  
  - body: `InsightsSnapshot` (+ report type: gtm | marketing | early_adopters)  
  - map DTO → existing `GTMRequest` / `MarketingRequest` fields (adapt generators; don’t rewrite MultiAgent stack)  
- Keep Firebase report save if Aureyo still uses it  
- Deploy Cloud Run on **cognispace** (or keep voicesense and VPC-connect — prefer **move/redeploy to cognispace** for one project)  
- CORS: allow Aureyo origin

#### 3) `stateboard` (.NET + React)

- Keep TF→hex path  
- Add controllers:  
  - `GET /api/products` → kih | lindle | yca  
  - `GET /api/insights/cost?product=` → BQ  
  - `GET /api/insights/health?product=` → from inventory config + optional Monitoring  
- Embed inventory YAML/JSON from Analytics plan (service list) as `dim_service` seed  
- Web: tabs **Map** | **Cost** | **Health**; link “Open Decide report” → Aureyo URL with `?product=`

#### 4) `Aureyo` (TS frontend)

- Product switcher (three apps)  
- Dashboard strip: load snapshot DTO (via insights-query or Raporting proxy)  
- Button: “Generate decision report” → Raporting  
- Nav link: “Platform / Prove” → Stateboard URL  
- Soft fusion = this + Stateboard link; hard fusion later = iframe or shared layout package from `asset_management`

### Auth (keep boring)

| Phase | Approach |
| --- | --- |
| v1 (you only) | IAP or simple shared secret / Google login on Cloud Run; no unified IdP |
| v2 | One Google OAuth / Firebase Auth issuer; all three validate same audience |

### What not to do technically

- Monorepo merge of .NET + Python + CRA  
- Calling BigQuery **from the browser** with a powerful key  
- Duplicating Billing ETL inside Stateboard and Raporting  
- Rewriting Raporting MultiAgent from scratch  
- New fourth “insights-api” **and** fat logic in both apps — pick **either** thin query CF **or** BQ views + server clients, not three pipelines

### Implementation order (engineering)

| # | Work | Repo / place | Depends on |
| --- | --- | --- | --- |
| 1 | GA4 → BQ + Billing → BQ in cognispace | GCP | — |
| 2 | SQL views → `InsightsSnapshot` table/API | cognispace | 1 |
| 3 | `POST /v1/insights/report` from DTO | Raporting | 2 |
| 4 | Aureyo: product picker + call report | Aureyo | 3 |
| 5 | Stateboard: cost + health from BQ/inventory | stateboard | 1–2 |
| 6 | Cross-links Decide ↔ Prove | Aureyo + stateboard | 4–5 |
| 7 | (Optional) monorepo / shared UI kit | later | stable contracts |

### Local dev

```bash
# Terminal A — Raporting
cd Raporting && uvicorn main:app --reload --port 8000

# Terminal B — Stateboard API
dotnet run --project src/Stateboard.Api --urls http://localhost:5281

# Terminal C — Stateboard web
cd apps/web && npm run dev

# Terminal D — Aureyo
cd Aureyo/Aureyo.Frontend && npm start
```

Point Aureyo `VITE_RAPORTING_URL` / Stateboard `Insights:BaseUrl` at local or Cloud Run; BQ via ADC (`gcloud auth application-default login`).

---

## Keep / cut / park — how to decide (per repo)

### Decision rule (use on every folder/feature)

Ask, in order:

1. **Does it answer an Insights question (A–E) or produce the Decide/Prove UX?** → **KEEP / extend**  
2. **Is it only needed to generate or display that answer (generator, DTO, BQ client)?** → **KEEP**  
3. **Is it a demo/hackathon/other-product leftover that isn’t on the fusion path?** → **PARK** (leave in repo, no new work, hide from UI)  
4. **Does it conflict, duplicate, or cost ops with zero Insights value?** → **DELETE** (or archive branch)  
5. **Unsure?** → **PARK** for 30 days; if unused in fusion milestones → DELETE

| Label | Meaning | Engineering |
| --- | --- | --- |
| **KEEP** | On the critical path | Fix, test, deploy |
| **EXTEND** | KEEP + new Insights work | Priority backlog |
| **PARK** | Don’t break; don’t invest | No tickets unless blocking |
| **DELETE** | Remove from default build/UI/deploy | Delete code or stop deploying |

### `stateboard` — Prove

| Area | Decision | Why |
| --- | --- | --- |
| `Stateboard.Api` + `Stateboard.Core` (HCL scan, graph) | **KEEP** | Core Prove differentiator |
| `apps/web` hex map | **KEEP** | Prove UI |
| `packages/tf-cost` / pricebook | **KEEP** | Cost narrative (complement Billing later) |
| `fixtures/sample-terraform` | **KEEP** | Dev/demo |
| tests, terraform deploy, CI | **KEEP** | Ship Prove |
| New: BQ cost/health endpoints, product switcher | **EXTEND** | Fusion |
| PH-only marketing fluff / unused experiments in docs | **PARK** | Don’t block |
| Anything that scans unrelated products’ TF with no Insights link | **PARK** until product picker exists | Scope creep |

**Delete candidates:** dead UI routes, unused Knot/cache artifacts in repo, duplicate sample apps not referenced by sln — only after `git grep` shows zero refs.

### `Raporting` — Decide engine

| Area | Decision | Why |
| --- | --- | --- |
| FastAPI `main` + `raports/router` | **KEEP** | Entry |
| `marketing_*` / `gtm_*` / `early_adopters_*` | **KEEP** | Business decision reports |
| `brief_doc_*` | **KEEP** if used by Aureyo; else **PARK** | Check callers |
| `summary_generator` / generic plan | **PARK** unless Insights snapshot uses them | Other products (AS/QC) historically |
| `MultiAgent/doc_gen` + `structure` (generic multi-agent PDF) | **PARK** | Heavy; not required for v1 snapshot→GTM |
| GCS `GCPClientBucket` | **KEEP** if reports stored in GCS | |
| Firebase save of reports | **KEEP** while Aureyo uses it; **PARK** migrate to BQ later | |
| Hardcoded CORS for aiviralbuzz / authenticscope | **DELETE** unused origins when deploying for Aureyo/Insights | Shrink attack surface |
| `firebase.json` secrets in repo | **DELETE from git** → Secret Manager | Security |

**Delete candidates:** generators with no route + no Aureyo call; PDF samples not referenced; voicesense-only deploy docs once moved to cognispace.

### `Aureyo` — Decide UI

| Area | Decision | Why |
| --- | --- | --- |
| Frontend pages for reports / dashboard | **KEEP / EXTEND** | Decide shell |
| Services calling Raporting | **KEEP / EXTEND** | |
| Points / subscription / payments UI | **PARK** | Monetization later; not Insights v1 |
| Reddit / MAS audience flows | **PARK** | Out of A–E unless you explicitly want channel research |
| Notion serverless (`getNotionData`) | **PARK** | Legacy; not BQ spine |
| Arcmind duplicate landing | **DELETE** or never open (lives other repo) | Portfolio already said merge |
| Points Firebase tables usage | **PARK** | |

**Delete candidates:** unpaid hackathon screens, dead routes, duplicate brand onboarding forms once snapshot replaces “brand_onboard” forms (per Raporting comment).

### Cross-repo (portfolio)

| Repo | For Insights fusion |
| --- | --- |
| `Arcmind` | **Don’t use** — fold into Aureyo or ignore |
| `Prospecting` / `MultiAgentSystem` | **PARK** for Insights v1 (unless Raporting calls MAS — then only that client) |
| `asset_management` | **PARK** until shared UI kit needed |
| `grafana-service` | **PARK** (Grafana postponed) |
| New insights repo | **DELETE idea** — don’t create |

### Practical process (do this once per repo)

1. List **entrypoints**: HTTP routes, npm pages, Cloud Run services.  
2. Tag each: KEEP / EXTEND / PARK / DELETE using the rule above.  
3. For DELETE: remove from router + UI nav first (soft delete), deploy, then delete files next PR.  
4. For PARK: add `# PARKED — Insights fusion` comment + no CI fail on that path.  
5. Revisit PARK list after Step 4 of fusion (cross-links live).

### Default bias for Insights

- Prefer **PARK over DELETE** in week 1 (less risk).  
- Prefer **DELETE deploy/CORS/secrets noise** immediately.  
- Prefer **EXTEND** only what serves `InsightsSnapshot` or Decide/Prove UX.

---

## Phased delivery (practical)

### Phase 0 — Inventory & questions (½–1 d)

- [x] Fill product table (GA4 / UX / Langfuse / GCP / billing / DB)  
- [x] Pick **BQ hub** = `cognispace`  
- [x] UX SoT = **Contentsquare** (Clarity legacy noted)  
- [x] Questions shortlist (shared A–E + product add-ons)  
- [ ] **Service inventory** via `gcloud run services list` (3 projects)  
- [ ] Consent/PHI note for KIH  
- [ ] Label standard applied on new resources (`product`, `env`)  
- [ ] Grafana — **postponed**

**Exit (revised):** IDs + hub + questions ✅ · service list ⬜ · then Phase 1.

### Phase 1 — GA4 → BQ on hub `cognispace` (1–2 d)

- [ ] GA4 → BigQuery **daily** export for one property first (KIH or Lindle or YCA) → dataset in **`cognispace`**  
- [ ] Looker Studio on that export  
- [ ] Clone export for the other two properties  

### Phase 2 — Contentsquare as UX companion (½–1 d)

- [ ] Confirm Contentsquare on each product (YCA may still be Hotjar/Clarity-heavy — align)  
- [ ] Runbook: Looker/GA4 dip → open Contentsquare on that URL/flow  
- [ ] Clarity: keep IDs only; no new Clarity build  

**(Grafana phases stay in plan but start after Monitoring/Looker path works.)**

### Phase 3 — App truth into BQ (2–4 d, one product)

- [ ] Ingest core tables: users, accounts, key entities (orders/subs/bookings as relevant) → `raw.app`  
- [ ] First `dim_user` + `fct_*` for that product’s truth events  
- [ ] Looker: “signup in app” vs “signup in GA4” reconciliation  

**Exit:** business outcome metrics come from app DB, not GA4 guesses.

### Phase 4 — Infra + Grafana product health + healthboard (1–2 d)

- [ ] Grafana folders × 3; Cloud Run KPIs  
- [ ] **Healthboard**: one row per service (health 🟢/🔴, last check, exceptions 1h)  
- [ ] Uptime checks (Cloud Monitoring) **or** scrape `/health` for every service in inventory  
- [ ] Wire **exceptions**: Error Reporting and/or Logging → Grafana panel + alert on surge  
- [ ] Selected metrics → `raw.gcp` / BQ; optional `fct_healthchecks` / `fct_exceptions`  
- [ ] Grafana BigQuery panels: DAU/activation next to error/latency/health  
- [ ] Annotations for deploys/incidents where possible  
- [ ] Alerts: **health FAIL**, 5xx spike, **exception surge**, latency  

**Exit:** can see all services’ health at a glance; red cell always has exception context when available; “checkout ↓ after deploy” correlation possible.

### Phase 4c — GCP Billing → BQ detailed cost (1 d, can parallel 4 / 4b)

- [ ] Enable **Billing export → BigQuery** (detailed usage cost) on the billing account(s)  
- [ ] Confirm tables appear in hub (`raw.billing` / export dataset)  
- [ ] Apply / backfill **labels** `product` + `env` on Cloud Run / SQL / key resources  
- [ ] dbt/sql: `stg_gcp_billing` → `fct_gcp_cost`  
- [ ] Looker page **Cloud cost**: by product, service, SKU, month  
- [ ] Grafana: daily cloud burn + budget threshold alerts  
- [ ] Join view: `marts.cost` = cloud (Billing) + LLM (Langfuse) by product/day  

**Exit:** know **$ GCP / day / product** at service (and SKU) detail — not only a single invoice total.

### Phase 4b — Langfuse → BQ + AI ops (1–2 d, after tags exist)
- [ ] Standardize Langfuse metadata (`user_id`, `session_id`, `account_id`, `product`, `feature`) on KIH (+ Lindle agents)  
- [ ] ETL: Langfuse API → `raw.langfuse` (daily)  
- [ ] dbt/sql: `fct_llm_traces`, `fct_llm_generations` (+ RAG spans if present)  
- [ ] Looker page **AI**: cost, tokens, latency, errors by product/feature  
- [ ] Grafana: AI cost burn + error rate alerts (budget / anomaly)  
- [ ] Runbook: metric dip → Langfuse trace filter by `user_id` / `session_id`  

**Exit:** know **$ AI / day / product** and can open the failing trace in Langfuse in &lt;2 min.

### Phase 5 — dbt core + product + AI marts (ongoing)

- [ ] dbt (or Dataform) project: staging → core → marts  
- [ ] Clean `fct_events` flattening GA4 + app events  
- [ ] First marts: adoption, funnel, retention, **`marts.ai`**, **`marts.cost`**, **`marts.reliability`**  
- [ ] Event taxonomy enforced in app + GTM + Langfuse tag docs  
- [ ] Join AI + GCP cost into `marts.revenue` / customer health where useful  

**Exit:** analysts query marts, not raw GA4/Langfuse/Billing APIs.

### Phase 6 — Optional next level

- [ ] Managed Prometheus `/metrics` on one API  
- [ ] Pub/Sub event pipeline for high-volume app events  
- [ ] Customer health score mart (include AI engagement + cost)  
- [ ] Langfuse scores/evals in marts (quality trends by prompt version)  
- [ ] BQML churn/activation experiments  
- [ ] **Not** GKE unless a real k8s need  

---

## Decision rules

| Do | Don’t |
| --- | --- |
| BQ = source of truth for aggregates | Build warehouse only on GA4 |
| App DB = business outcomes | Infer payments/orders from GA4 |
| **Billing export = cloud $ detail** | Guess cost from Monitoring charts alone |
| Label resources `product` / `env` | One unlabeled shared project forever |
| Langfuse = LLM/RAG system of record | Replace Langfuse UI with BQ for debugging |
| Clarity = why / UX | Replicate all Clarity into BQ |
| Looker = strategy + AI + **cloud cost** | Use Grafana as only BI |
| Grafana = healthboard + infra + AI + billing burn | Ignore exceptions next to red health |
| Every service has `/health` (or uptime check) | “Unknown” services with no probe |
| Exceptions visible when health/errors fail | Red status with no evidence |
| Tag every trace for join keys | Untagged traces that can’t join to users |
| Start from 10–18 questions | Create 500 tables “just in case” |
| Consent-aware identity; PHI-safe prompts | Blind ID stitch; dump full PHI prompts to BQ |

---

## Rough effort

| Phase | Effort | Depends on |
| --- | --- | --- |
| 0 | 0.5–1 d | Access |
| 1 | 1–2 d | GA4 admin + BQ |
| 2 | 0.5–1 d | Clarity admin |
| 3 | 2–4 d | DB access, one product |
| 4 | 1–2 d | Grafana project fix |
| 4c | ~1 d | Billing admin + BQ hub |
| 4b | 1–2 d | Langfuse tags + API access |
| 5 | ongoing | Phase 3–4b/4c stable |
| 6 | optional | Phase 5 useful |

**Order this month:** paid path first → Phase 0 + Grafana fix → Phase 1 one product → 2 → 3 → 4 → **4c Billing export** → **4b KIH Langfuse** → dbt marts.

---

## Deliverables

| Artifact | Where |
| --- | --- |
| This plan + filled inventory | this note |
| Question list (10–20) | this note / per product |
| BQ datasets `raw` / `staging` / `core` / `marts` (+ langfuse, billing, **reliability**/health) | hub GCP project |
| GCP Billing export enabled (detailed) | Billing account → hub BQ |
| Label standard `product` / `env` | Terraform / runbooks |
| Looker Studio: Platform Insights + AI + **Cloud cost** | Looker |
| Grafana: **healthboard** + folders + BQ + AI burn + cloud burn + **exceptions** | existing Grafana |
| Service inventory + `/health` contract | per product runbook |
| Langfuse tag standard | short doc; enforced in KIH/Lindle agents |
| Event taxonomy doc | short markdown next to apps |
| dbt/Dataform repo | when Phase 5 starts |

## Related

- [[00 System/Current Focus]] — don’t block employment / CVs  
- [[01 Initiatives/Keep It Healthy/Dr Kiwi/# Dr Kiwi — Current State]] — Gemini + Langfuse  
- [[01 Initiatives/Lindle/Metrics]] — Langfuse for agents  
- Products: Lindle · Keep It Healthy / Dr Kiwi · CzatBudowlany  
- Grafana (shared Cloud Run) — ops + AI burn + later BQ product health
