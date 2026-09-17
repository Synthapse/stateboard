# UI setup — all load paths (cognispace hub)

One-time setup in **GA4 / GCP Billing / Langfuse / Contentsquare / Clarity** UIs  
so Narrate can fill `marts_insights.snapshot_daily`.

Strategy: [strategy-recommendation.md](./strategy-recommendation.md) · Architecture: [insights-architecture.md](./insights-architecture.md).  
Code: `Narrate/insights/integrations/`.

**Hub:** `cognispace` · **BQ location:** `EU`

---

## 0. Terraform

```bash
cd terraform && terraform apply
```

Creates `raw_*`, `staging.*`, `core.*`, `marts.*`, `marts_insights.*` (see `terraform/bigquery.tf`).

---

## 1. GA4 → BigQuery

| Product | Property | Measurement | Dataset |
|---------|----------|-------------|---------|
| KIH | `499549002` | `G-CBTHK8QQ6N` | `analytics_499549002` |
| Lindle | `506154105` | `G-71BSGEPP21` | `analytics_506154105` |
| YCA | `494547928` | `G-DZNYJF6HSB` | `analytics_494547928` |

1. [analytics.google.com](https://analytics.google.com/) → property  
2. **Admin** → **Product links** → **BigQuery Links** → **Link**  
3. Project **`cognispace`**, location **EU**, frequency **Daily** → Submit  

---

## 2. GCP Billing → BigQuery

| Product | Billing account | Cost project | Export destination |
|---------|-----------------|--------------|--------------------|
| KIH | `01BF64-6A600F-517AFE` | `dr-kiwi-app` | Stage `dr-kiwi-app.raw_billing` → daily TF copy → `cognispace.raw_billing` |
| Lindle | `01C7B7-5B77CD-27EDAD` | `cognispace` | **Direct** → `cognispace.raw_billing` |
| YCA | `01F545-2E8963-C6EBE1` | `adroit-router-462912-n6` | Stage `adroit-router-….raw_billing` → daily TF copy → hub |

### Lindle (direct — Cognispace is on Lindle billing)

1. Console → **Billing** → Lindle account → **Billing export** → **BigQuery export**  
2. **Detailed usage cost** ON → project **`cognispace`** → dataset **`raw_billing`**  

### YCA / KIH (bridge — Cognispace is on Lindle billing)

1. Detailed export → **product’s own GCP project** → dataset `raw_billing` (EU)  
2. Terraform sync (`kih_billing_sync.tf` / `yca_billing_sync.tf`) copies into `cognispace.raw_billing` daily  
3. Hub tables: YCA `…_01F545_…` · KIH `…_01BF64_…` (KIH still needs Console export first)

---

## 3. Langfuse → Digests / `raw_langfuse` (required lens)

Not a native BQ export — create **API keys** in Langfuse UI; Narrate ETL pulls cost/traces.

| Product | Project name | Project id | Org |
|---------|--------------|------------|-----|
| KIH | DrKiwi | `cmph5si3406aoad0e8o2j8p4d` | Keep It Healthy |
| Lindle | Lindle | `cmei38jmn00s1ad07oqzvyqcz` | Synthapse |
| YCA | yca-ca-mvp | (set if different) | — |

### UI steps (each Langfuse project)

1. Open [cloud.langfuse.com](https://cloud.langfuse.com) (EU) → select project  
2. **Settings** → **API Keys** → **Create** new public + secret key  
3. Put keys in `Narrate/.env` (never commit):

```bash
LANGFUSE_HOST=https://cloud.langfuse.com
# shared fallback:
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
# or per product:
LANGFUSE_KIH_PUBLIC_KEY=...
LANGFUSE_KIH_SECRET_KEY=...
LANGFUSE_LINDLE_PUBLIC_KEY=...
LANGFUSE_LINDLE_SECRET_KEY=...
LANGFUSE_YCA_PUBLIC_KEY=...
LANGFUSE_YCA_SECRET_KEY=...
```

4. Tag traces with `product=kih|lindle|yca` (app code) for clean joins later  

### Daily ETL → BigQuery

Narrate pulls Langfuse Metrics API and upserts **one row per product × day** into  
`cognispace.raw_langfuse.daily_metrics`.

```bash
cd Narrate
# yesterday for all products (needs LANGFUSE_* keys + BQ ADC)
python -c "from insights import langfuse_etl; print(langfuse_etl())"

# backfill last 7 days
python -c "from insights import langfuse_etl; print(langfuse_etl(lookback_days=7))"
```

HTTP (Cloud Function): `?action=langfuse_etl` (all) or `?action=langfuse_etl&product=lindle`.

**Schedule daily** (Cloud Scheduler → that HTTP endpoint), e.g. `0 6 * * *` UTC.

`build_snapshots` still calls Langfuse live for Digest `ai_cost_usd`; the ETL is the durable history in BQ.

---

## 4. Contentsquare → Digests (UX SoT)

Contentsquare is the **UX system of truth** (Clarity is legacy). Digests register the project and optionally call the API for a friction skim — not a full session warehouse.

| Product | Contentsquare project id |
|---------|--------------------------|
| KIH | `57dec74d2513b` |
| Lindle | set in CS Console / `CONTENTSQUARE_LINDLE_PROJECT_ID` |
| YCA | set in CS Console / `CONTENTSQUARE_YCA_PROJECT_ID` |

### UI steps

1. Log in to **Contentsquare** Console for each product  
2. Confirm / copy **Project ID** (KIH already in registry)  
3. **Settings → API / Integrations** → create API credential (if your plan includes API)  
4. Env:

```bash
CONTENTSQUARE_API_KEY=...
# optional overrides:
CONTENTSQUARE_KIH_PROJECT_ID=57dec74d2513b
CONTENTSQUARE_LINDLE_PROJECT_ID=...
CONTENTSQUARE_YCA_PROJECT_ID=...
```

Without an API key, Digests still record `contentsquare:missing_id|no_api_key` in Snapshot flags so the gap is visible.

---

## 5. Clarity → Digests (legacy IDs + export API)

Keep Clarity project IDs for continuity; do **not** treat Clarity as UX SoT.

| Product | Clarity project id |
|---------|-------------------|
| KIH | — (none) |
| Lindle | `tfa09ihgyu` |
| YCA | `t9jhgsv5zv` |

### UI steps

1. [clarity.microsoft.com](https://clarity.microsoft.com/) → project  
2. **Settings** → **Data Export** / API → generate **API token**  
3. Env:

```bash
CLARITY_API_TOKEN=...
# optional:
CLARITY_LINDLE_PROJECT_ID=tfa09ihgyu
CLARITY_YCA_PROJECT_ID=t9jhgsv5zv
```

`build_snapshots` checks export reachability and adds `clarity:…` flags.

### Daily ETL → BigQuery

```bash
cd Narrate
python3 -c "from insights import clarity_etl; print(clarity_etl())"
```

Writes `cognispace.raw_clarity.daily_insights` (full API JSON for last 1–3 days).  
Clarity API limits: **max 3 days history**, **~10 requests/project/day** — run once daily.

---

## 6. Run Snapshot build

```bash
cd Narrate
export DIGEST_USE_FIXTURE=0 BQ_PROJECT=cognispace BQ_LOCATION=EU
# + LANGFUSE_* / CONTENTSQUARE_* / CLARITY_* as above

python -c "from insights import build_snapshots, Product; print(build_snapshots(Product.KIH))"
python -c "from insights import digest_run, Product; print(digest_run(Product.KIH)['text'])"
```

---

## Automation

| Lens | You set up once | Then |
|------|-----------------|------|
| GA4 | BigQuery Link | Daily `events_*` |
| Billing | Detailed export | Continuous rows |
| Langfuse | API keys in `.env` | `build_snapshots` ETL each run |
| Contentsquare | Project id + API key | Signal on each Snapshot build |
| Clarity | Project id + token | Signal on each Snapshot build |
| Snapshot + Digest | Scheduler (M5) | Cadence automation |

---

## 7. Digest email audiences (required)

Each product has its **own** recipient list. Set in `Narrate/.env` (never commit):

```bash
DIGEST_CHANNEL=email
DIGEST_EMAIL_TO=piotrzak77@gmail.com          # fallback if product unset

DIGEST_EMAIL_TO_KIH=piotrzak77@gmail.com
DIGEST_EMAIL_TO_LINDLE=piotrzak77@gmail.com,alice@example.com
DIGEST_EMAIL_TO_YCA=piotrzak77@gmail.com
```

- Comma-separated = multiple people on that product’s Digest  
- SMTP (`SMTP_*`) must be set so mail actually sends  
- Every send is also written to BigQuery: `marts_insights.digest_delivery` (subject, body, audience, delivered)

Update audiences whenever stakeholders change — no code change needed.

---

## Checklist

- [ ] TF apply  
- [ ] GA4 links ×3 → cognispace / EU  
- [ ] Billing Detailed export ×3 → `raw_billing`  
- [ ] Langfuse API keys + daily `langfuse_etl` → `raw_langfuse.daily_metrics`  
- [ ] Contentsquare project ids (+ API key)  
- [ ] Clarity tokens for Lindle + YCA  
- [x] SMTP (Gmail App Password) + test Digest email → `piotrzak77@gmail.com`  
- [x] **Set per-product audiences** (`DIGEST_EMAIL_TO_KIH` / `_LINDLE` / `_YCA`)  
- [ ] `build_snapshots` → row with GA4/Billing/Langfuse/UX flags  
- [ ] `digest_run` shows BigQuery details + AI $

### Status snapshot (2026-09-16)

| Check | Result |
|-------|--------|
| Lindle GA4 `analytics_506154105` | Linked; `events_*` present |
| YCA GA4 `analytics_494547928` | Linked; `events_*` present |
| KIH GA4 `analytics_499549002` | Linked; `events_*` present |
| Billing Lindle | In `cognispace.raw_billing` |
| Billing YCA | Stage + hub copy present (`01F545_…`) |
| Billing KIH | **Blocked** — enable Detailed export on billing account → `dr-kiwi-app.raw_billing` (sync TF already exists) |
| Scheduler | `insights-daily-pipeline` + `insights-weekly-digest` ENABLED |
| Audiences | All three → `piotrzak77@gmail.com` (edit when stakeholders known) |

### BigQuery cost hygiene

Insights jobs should stay cheap if you:

- Run **daily** (not every few minutes) — `build_snapshots` / Digests / Langfuse / Clarity  
- Rely on **partition filters**: GA4 uses `_TABLE_SUFFIX`; Billing uses `_PARTITIONTIME` + lookback  
- Keep lookback at **7 days** (default) unless you need more  
- Cap scanned bytes: `BQ_MAX_BYTES_BILLED` (default **50 GiB** per query — job fails instead of a surprise bill)

Watch: [Billing → Reports](https://console.cloud.google.com/billing) filtered to BigQuery, or job stats in BQ UI (`totalBytesProcessed`). Marts writes (`snapshot_daily`, `digest_delivery`) are tiny; **Billing export scans** are the main risk as that table grows.
