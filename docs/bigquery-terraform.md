# BigQuery via Terraform (no Ansible)

Insights warehouse in **`cognispace`** — full layout from
[Analytics & Insights Plan.md](./Analytics%20%26%20Insights%20Plan.md), plus Digest tables.

Declared in [`../terraform/bigquery.tf`](../terraform/bigquery.tf).  
Load paths / UI: [bigquery-load-paths.md](./bigquery-load-paths.md) · [ui-setup-load-paths.md](./ui-setup-load-paths.md).

## What `terraform apply` creates

### Raw datasets

| Dataset | Purpose |
|---------|---------|
| `raw_billing` | GCP Billing Detailed export |
| `raw_langfuse` | Langfuse ETL — table `daily_metrics` (product × day) |
| `raw_clarity` | Clarity API aggregates |
| `raw_contentsquare` | Contentsquare (UX SoT) |
| `raw_app` | App DB / events |
| `raw_gcp` | Monitoring / Logging exports |
| `raw_health` | Healthchecks / exceptions |
| `analytics_<property_id>` | GA4 native export (from `ga4_dataset_ids`) |

### Staging (`staging.*`)

`stg_ga4_events` · `stg_langfuse_traces` · `stg_langfuse_observations` · `stg_langfuse_scores` ·  
`stg_gcp_billing` · `stg_service_health` · `stg_exceptions` · `stg_users` · `stg_accounts` ·  
`stg_orders` · `stg_clarity` · `stg_contentsquare`

### Core (`core.*`)

**Dims:** `dim_user` · `dim_account` · `dim_product` · `dim_feature` · `dim_prompt` · `dim_model` ·  
`dim_gcp_service` · `dim_service`  

**Facts:** `fct_events` · `fct_sessions` · `fct_llm_traces` · `fct_llm_generations` ·  
`fct_rag_retrievals` · `fct_gcp_cost` · `fct_healthchecks` · `fct_exceptions` ·  
`fct_orders` · `fct_subscriptions`

### Marts (`marts.*`)

`product` · `ai` · `cost` · `reliability` · `marketing` · `revenue` · `customer` · `executive` · `growth`

### Digests (`marts_insights.*`)

| Table | Purpose |
|-------|---------|
| `snapshot_daily` | InsightsSnapshot (typed Digests contract) |
| `product_strategy` | Living GTM ProductStrategyHold |

Layer schemas differ (not one shared skeleton):

| Layer | Shape | Partition |
|-------|--------|-----------|
| `staging.*` | `source_system`, `ingest_date`, `payload_json`, … | `ingest_date` |
| `core.dim_*` | `id`, SCD fields (`valid_from` / `valid_to` / `is_current`), `attributes_json` | — |
| `core.fct_*` | `event_ts`, `product`, metrics / `props_json` | `event_ts` |
| `marts.*` | `period_date`, `product`, `metrics_json` | `period_date` |
| `marts_insights.*` | Full Digest contracts | `period_date` |

Promote JSON blobs to typed columns when dbt / scheduled SQL lands.

## What TF does *not* fill

- Row data (GA4 Link, Billing export, Langfuse/CS/Clarity ETL, dbt)
- Cloud Scheduler / Digest Function deploy

## Apply

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars   # review ga4_dataset_ids
terraform init && terraform plan && terraform apply
```

Use `bq_location = "EU"` (match GA4 export).

```bash
terraform output bq_datasets
```

### Note on older empty datasets

Previous MVP used separate `marts_growth` / `marts_cost` / … datasets. Those are **replaced** by tables under `marts` + `marts_insights`. If you already applied the old TF, `terraform apply` will destroy the empty legacy datasets and create the full plan structure.
