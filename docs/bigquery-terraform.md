# BigQuery via Terraform (no Ansible)

Insights warehouse lives in **`cognispace`**. Structure is declared in [`../terraform/bigquery.tf`](../terraform/bigquery.tf).

## Ansible?

**No.** BQ has no VMs to configure. Terraform `google_bigquery_dataset` / `google_bigquery_table` is enough. Optional later: **scheduled queries** or **dbt** for marts SQL — still not Ansible.

## What TF creates

| Dataset | Purpose |
|---------|---------|
| `raw_billing` | Landing for Billing export |
| `raw_langfuse` | Later |
| `raw_ga4_*` | Optional empty shells (`ga4_dataset_ids`); usually GA4 linking creates these |
| `marts_growth` / `marts_cost` / `marts_reliability` / `marts_ai` | Aggregates for Digests |
| `marts_insights.snapshot_daily` | **InsightsSnapshot** contract table |

## What TF does *not* own (yet)

- GA4 Admin → BigQuery link (creates `events_*` tables)
- Billing export sink configuration (point it at `raw_billing`)
- Digest Cloud Function / Scheduler (MVP can be `gcloud`)

## Apply

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars   # edit if needed
terraform init
terraform plan    # review BQ + existing Stateboard resources
terraform apply
```

Use `bq_location = "EU"` (or match your GA4 export location).
