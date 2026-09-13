# Insights BigQuery hub (cognispace)
# Schema / datasets only — no Ansible. GA4 & Billing exports fill raw_* via Google linking UIs.
# Apply: terraform plan/apply from this directory (project_id = cognispace).

locals {
  bq_location = var.bq_location
  insights_labels = {
    app        = "insights"
    managed_by = "terraform"
  }
}

# --- Raw (landing) -----------------------------------------------------------

resource "google_bigquery_dataset" "raw_billing" {
  dataset_id                 = "raw_billing"
  friendly_name              = "Raw GCP Billing export"
  description                = "Billing export landing. Link billing account → this dataset in Cloud Console."
  location                   = local.bq_location
  delete_contents_on_destroy = false
  labels                     = local.insights_labels
}

resource "google_bigquery_dataset" "raw_langfuse" {
  dataset_id                 = "raw_langfuse"
  friendly_name              = "Raw Langfuse ETL"
  description                = "Optional later — Langfuse traces/cost landing."
  location                   = local.bq_location
  delete_contents_on_destroy = false
  labels                     = local.insights_labels
}

# GA4 creates one dataset per property when you enable BigQuery linking.
# We only declare placeholders you can create empty ahead of time (optional).
resource "google_bigquery_dataset" "raw_ga4" {
  for_each = toset(var.ga4_dataset_ids)

  dataset_id                 = each.value
  friendly_name              = "Raw GA4 ${each.value}"
  description                = "GA4 BigQuery export dataset. Prefer linking from GA4 Admin → BigQuery Links."
  location                   = local.bq_location
  delete_contents_on_destroy = false
  labels                     = local.insights_labels
}

# --- Marts (Insights-owned) --------------------------------------------------

resource "google_bigquery_dataset" "marts_growth" {
  dataset_id                 = "marts_growth"
  friendly_name              = "Marts — growth"
  description                = "Aggregated GA4/app growth metrics for Digests."
  location                   = local.bq_location
  delete_contents_on_destroy = false
  labels                     = local.insights_labels
}

resource "google_bigquery_dataset" "marts_cost" {
  dataset_id                 = "marts_cost"
  friendly_name              = "Marts — cloud cost"
  description                = "Aggregated Billing metrics by product label."
  location                   = local.bq_location
  delete_contents_on_destroy = false
  labels                     = local.insights_labels
}

resource "google_bigquery_dataset" "marts_reliability" {
  dataset_id                 = "marts_reliability"
  friendly_name              = "Marts — reliability"
  description                = "Job/queue/health flags for Digests."
  location                   = local.bq_location
  delete_contents_on_destroy = false
  labels                     = local.insights_labels
}

resource "google_bigquery_dataset" "marts_ai" {
  dataset_id                 = "marts_ai"
  friendly_name              = "Marts — AI / Langfuse"
  description                = "LLM cost/quality skim for Digests."
  location                   = local.bq_location
  delete_contents_on_destroy = false
  labels                     = local.insights_labels
}

resource "google_bigquery_dataset" "marts_insights" {
  dataset_id                 = "marts_insights"
  friendly_name              = "Marts — Insights snapshots"
  description                = "Materialized InsightsSnapshot rows for Digests."
  location                   = local.bq_location
  delete_contents_on_destroy = false
  labels                     = local.insights_labels
}

# Contract table: one row per product × day (or period). Digest Function reads latest.
resource "google_bigquery_table" "insights_snapshot_daily" {
  dataset_id = google_bigquery_dataset.marts_insights.dataset_id
  table_id   = "snapshot_daily"
  project    = var.project_id

  description = "InsightsSnapshot v1 — vital-few metrics per product per day"

  time_partitioning {
    type  = "DAY"
    field = "period_date"
  }

  clustering = ["product"]

  schema = jsonencode([
    { name = "period_date", type = "DATE", mode = "REQUIRED", description = "Snapshot day (UTC)" },
    { name = "product", type = "STRING", mode = "REQUIRED", description = "kih | lindle | yca" },
    { name = "schema_version", type = "INT64", mode = "REQUIRED", description = "InsightsSnapshot schema_version" },
    { name = "period_start", type = "TIMESTAMP", mode = "NULLABLE" },
    { name = "period_end", type = "TIMESTAMP", mode = "NULLABLE" },
    { name = "sessions", type = "INT64", mode = "NULLABLE" },
    { name = "sessions_delta_pct", type = "FLOAT64", mode = "NULLABLE" },
    { name = "users", type = "INT64", mode = "NULLABLE" },
    { name = "cloud_cost_usd", type = "FLOAT64", mode = "NULLABLE" },
    { name = "cloud_cost_delta_pct", type = "FLOAT64", mode = "NULLABLE" },
    { name = "ai_cost_usd", type = "FLOAT64", mode = "NULLABLE" },
    { name = "reliability_flags", type = "STRING", mode = "REPEATED", description = "Short flags e.g. job:cds-purge-events:FAILED" },
    { name = "watch_bullets", type = "STRING", mode = "REPEATED", description = "Up to 3 action bullets" },
    { name = "payload_json", type = "JSON", mode = "NULLABLE", description = "Full InsightsSnapshot blob" },
    { name = "updated_at", type = "TIMESTAMP", mode = "REQUIRED" },
  ])
}
