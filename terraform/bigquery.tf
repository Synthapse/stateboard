# Insights BigQuery hub (cognispace)
# Insights warehouse: raw → staging → core → marts (+ marts_insights Digests)
# Strategy: docs/strategy-recommendation.md
# + marts_insights Digest contracts (snapshot_daily, product_strategy).
# GA4 native export uses analytics_<property_id> (also created via ga4_dataset_ids).
# Apply: terraform plan/apply from this directory (project_id = cognispace).

locals {
  bq_location = var.bq_location
  insights_labels = {
    app        = "insights"
    managed_by = "terraform"
  }

  # --- Dataset shells (plan layers) ------------------------------------------
  raw_datasets = {
    raw_billing       = "GCP Billing Detailed usage cost export"
    raw_langfuse      = "Langfuse API / ETL landing"
    raw_clarity       = "Clarity API aggregates / project links"
    raw_app           = "App DB / events landing (users, orgs, orders…)"
    raw_gcp           = "Monitoring / Logging / uptime / Error Reporting exports"
    raw_health        = "Curated healthcheck + exception events"
  }

  # Staging tables (dataset: staging)
  staging_tables = toset([
    "stg_ga4_events",
    "stg_langfuse_traces",
    "stg_langfuse_observations",
    "stg_langfuse_scores",
    "stg_gcp_billing",
    "stg_service_health",
    "stg_exceptions",
    "stg_users",
    "stg_accounts",
    "stg_orders",
    "stg_clarity",
  ])

  # Core dims vs facts (different schemas)
  dim_tables = toset([
    "dim_user",
    "dim_account",
    "dim_product",
    "dim_feature",
    "dim_prompt",
    "dim_model",
    "dim_gcp_service",
    "dim_service",
  ])

  fct_tables = toset([
    "fct_events",
    "fct_sessions",
    "fct_llm_traces",
    "fct_llm_generations",
    "fct_rag_retrievals",
    "fct_gcp_cost",
    "fct_healthchecks",
    "fct_exceptions",
    "fct_orders",
    "fct_subscriptions",
  ])

  # Marts product-facing (dataset: marts) — plan list + growth alias
  marts_tables = toset([
    "product",
    "ai",
    "cost",
    "reliability",
    "marketing",
    "revenue",
    "customer",
    "executive",
    "growth",
  ])

  # Layer-specific schemas (not identical placeholders)
  # staging = cleaned source rows
  staging_schema = jsonencode([
    { name = "source_system", type = "STRING", mode = "REQUIRED", description = "ga4 | billing | langfuse | clarity | app | gcp | health" },
    { name = "source_table", type = "STRING", mode = "NULLABLE", description = "Upstream table / export name" },
    { name = "ingest_date", type = "DATE", mode = "REQUIRED", description = "Partition = ingest day" },
    { name = "product", type = "STRING", mode = "NULLABLE", description = "kih | lindle | yca when known" },
    { name = "record_id", type = "STRING", mode = "NULLABLE", description = "Natural / surrogate id from source" },
    { name = "event_ts", type = "TIMESTAMP", mode = "NULLABLE" },
    { name = "payload_json", type = "JSON", mode = "REQUIRED", description = "Normalized staging payload" },
    { name = "ingested_at", type = "TIMESTAMP", mode = "REQUIRED" },
  ])

  # core dims = entities
  dim_schema = jsonencode([
    { name = "id", type = "STRING", mode = "REQUIRED", description = "Surrogate / natural key" },
    { name = "product", type = "STRING", mode = "NULLABLE", description = "kih | lindle | yca when scoped" },
    { name = "name", type = "STRING", mode = "NULLABLE" },
    { name = "attributes_json", type = "JSON", mode = "NULLABLE", description = "Dim attributes until fully typed" },
    { name = "valid_from", type = "TIMESTAMP", mode = "NULLABLE" },
    { name = "valid_to", type = "TIMESTAMP", mode = "NULLABLE" },
    { name = "is_current", type = "BOOL", mode = "NULLABLE" },
    { name = "updated_at", type = "TIMESTAMP", mode = "REQUIRED" },
  ])

  # core facts = events / measures
  fct_schema = jsonencode([
    { name = "event_ts", type = "TIMESTAMP", mode = "REQUIRED", description = "Fact timestamp (partition)" },
    { name = "product", type = "STRING", mode = "REQUIRED", description = "kih | lindle | yca" },
    { name = "entity_id", type = "STRING", mode = "NULLABLE", description = "FK-ish to dim (user, account, …)" },
    { name = "metric_name", type = "STRING", mode = "NULLABLE" },
    { name = "metric_value", type = "FLOAT64", mode = "NULLABLE" },
    { name = "cost_usd", type = "FLOAT64", mode = "NULLABLE" },
    { name = "status", type = "STRING", mode = "NULLABLE" },
    { name = "props_json", type = "JSON", mode = "NULLABLE" },
    { name = "updated_at", type = "TIMESTAMP", mode = "REQUIRED" },
  ])

  # marts = period × product aggregates for BI / Digests inputs
  marts_schema = jsonencode([
    { name = "period_date", type = "DATE", mode = "REQUIRED" },
    { name = "product", type = "STRING", mode = "REQUIRED" },
    { name = "cadence", type = "STRING", mode = "NULLABLE", description = "daily | weekly | monthly" },
    { name = "metrics_json", type = "JSON", mode = "REQUIRED", description = "Mart KPIs blob until columns are promoted" },
    { name = "updated_at", type = "TIMESTAMP", mode = "REQUIRED" },
  ])
}

# =============================================================================
# RAW
# =============================================================================

resource "google_bigquery_dataset" "raw" {
  for_each = local.raw_datasets

  dataset_id                 = each.key
  friendly_name              = each.key
  description                = each.value
  location                   = local.bq_location
  delete_contents_on_destroy = false
  labels                     = local.insights_labels
}

# Langfuse daily ETL landing (Narrate langfuse_etl)
resource "google_bigquery_table" "raw_langfuse_daily_metrics" {
  dataset_id          = google_bigquery_dataset.raw["raw_langfuse"].dataset_id
  table_id            = "daily_metrics"
  project             = var.project_id
  description         = "Langfuse API daily cost/traces per product (ETL upsert)"
  deletion_protection = false

  time_partitioning {
    type  = "DAY"
    field = "period_date"
  }

  clustering = ["product"]

  schema = jsonencode([
    { name = "product", type = "STRING", mode = "REQUIRED", description = "kih | lindle | yca" },
    { name = "period_date", type = "DATE", mode = "REQUIRED" },
    { name = "langfuse_project_id", type = "STRING", mode = "NULLABLE" },
    { name = "langfuse_project_name", type = "STRING", mode = "NULLABLE" },
    { name = "total_cost_usd", type = "FLOAT64", mode = "NULLABLE" },
    { name = "trace_count", type = "INT64", mode = "NULLABLE" },
    { name = "source", type = "STRING", mode = "NULLABLE" },
    { name = "ingested_at", type = "TIMESTAMP", mode = "REQUIRED" },
  ])
}

# Clarity daily ETL landing (Narrate clarity_etl) — last 1–3 days API payload
resource "google_bigquery_table" "raw_clarity_daily_insights" {
  dataset_id          = google_bigquery_dataset.raw["raw_clarity"].dataset_id
  table_id            = "daily_insights"
  project             = var.project_id
  description         = "Clarity Data Export API payload per product per run day"
  deletion_protection = false

  time_partitioning {
    type  = "DAY"
    field = "period_date"
  }

  clustering = ["product"]

  schema = jsonencode([
    { name = "product", type = "STRING", mode = "REQUIRED" },
    { name = "period_date", type = "DATE", mode = "REQUIRED" },
    { name = "clarity_project_id", type = "STRING", mode = "NULLABLE" },
    { name = "num_of_days", type = "INT64", mode = "NULLABLE" },
    { name = "payload_json", type = "JSON", mode = "NULLABLE" },
    { name = "status", type = "STRING", mode = "NULLABLE" },
    { name = "ingested_at", type = "TIMESTAMP", mode = "REQUIRED" },
  ])
}

# GA4 native export datasets (analytics_<property_id>) — optional pre-create
resource "google_bigquery_dataset" "raw_ga4" {
  for_each = toset(var.ga4_dataset_ids)

  dataset_id                 = each.value
  friendly_name              = "Raw GA4 ${each.value}"
  description                = "GA4 BigQuery Link export (events_*). Prefer linking from GA4 Admin."
  location                   = local.bq_location
  delete_contents_on_destroy = false
  labels                     = local.insights_labels
}

# =============================================================================
# STAGING
# =============================================================================

resource "google_bigquery_dataset" "staging" {
  dataset_id                 = "staging"
  friendly_name              = "Staging"
  description                = "Cleaned / typed staging tables (Analytics & Insights Plan)."
  location                   = local.bq_location
  delete_contents_on_destroy = false
  labels                     = local.insights_labels
}

resource "google_bigquery_table" "staging" {
  for_each            = local.staging_tables
  dataset_id          = google_bigquery_dataset.staging.dataset_id
  table_id            = each.value
  project             = var.project_id
  description         = "Staging — ${each.value} (cleaned source rows)"
  schema              = local.staging_schema
  deletion_protection = false

  time_partitioning {
    type  = "DAY"
    field = "ingest_date"
  }
}

# =============================================================================
# CORE
# =============================================================================

resource "google_bigquery_dataset" "core" {
  dataset_id                 = "core"
  friendly_name              = "Core"
  description                = "Dimensional model — dims + facts (Analytics & Insights Plan)."
  location                   = local.bq_location
  delete_contents_on_destroy = false
  labels                     = local.insights_labels
}

resource "google_bigquery_table" "core_dim" {
  for_each            = local.dim_tables
  dataset_id          = google_bigquery_dataset.core.dataset_id
  table_id            = each.value
  project             = var.project_id
  description         = "Core dim — ${each.value}"
  schema              = local.dim_schema
  deletion_protection = false
}

resource "google_bigquery_table" "core_fct" {
  for_each            = local.fct_tables
  dataset_id          = google_bigquery_dataset.core.dataset_id
  table_id            = each.value
  project             = var.project_id
  description         = "Core fact — ${each.value}"
  schema              = local.fct_schema
  deletion_protection = false

  time_partitioning {
    type  = "DAY"
    field = "event_ts"
  }

  clustering = ["product"]
}

# =============================================================================
# MARTS (plan product marts)
# =============================================================================

resource "google_bigquery_dataset" "marts" {
  dataset_id                 = "marts"
  friendly_name              = "Marts"
  description                = "Product-facing marts: product, ai, cost, reliability, …"
  location                   = local.bq_location
  delete_contents_on_destroy = false
  labels                     = local.insights_labels
}

resource "google_bigquery_table" "marts" {
  for_each            = local.marts_tables
  dataset_id          = google_bigquery_dataset.marts.dataset_id
  table_id            = each.value
  project             = var.project_id
  description         = "Mart — ${each.value} (period × product KPIs)"
  schema              = local.marts_schema
  deletion_protection = false

  time_partitioning {
    type  = "DAY"
    field = "period_date"
  }

  clustering = ["product"]
}

# =============================================================================
# MARTS_INSIGHTS — Digest contracts (Narrate)
# =============================================================================

resource "google_bigquery_dataset" "marts_insights" {
  dataset_id                 = "marts_insights"
  friendly_name              = "Marts — Insights Digests"
  description                = "InsightsSnapshot + ProductStrategyHold for Digests."
  location                   = local.bq_location
  delete_contents_on_destroy = false
  labels                     = local.insights_labels
}

resource "google_bigquery_table" "insights_snapshot_daily" {
  dataset_id          = google_bigquery_dataset.marts_insights.dataset_id
  table_id            = "snapshot_daily"
  project             = var.project_id
  deletion_protection = false

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

resource "google_bigquery_table" "insights_product_strategy" {
  dataset_id          = google_bigquery_dataset.marts_insights.dataset_id
  table_id            = "product_strategy"
  project             = var.project_id
  deletion_protection = false

  description = "ProductStrategyHold — GTM-like sections; refreshed each Digest cadence"

  time_partitioning {
    type  = "DAY"
    field = "period_date"
  }

  clustering = ["product", "cadence"]

  schema = jsonencode([
    { name = "period_date", type = "DATE", mode = "REQUIRED" },
    { name = "product", type = "STRING", mode = "REQUIRED" },
    { name = "cadence", type = "STRING", mode = "REQUIRED" },
    { name = "schema_version", type = "INT64", mode = "REQUIRED" },
    { name = "title", type = "STRING", mode = "NULLABLE" },
    { name = "product_description", type = "STRING", mode = "NULLABLE" },
    { name = "target_market", type = "STRING", mode = "NULLABLE" },
    { name = "budget_range", type = "STRING", mode = "NULLABLE" },
    { name = "timeline_constraints", type = "STRING", mode = "NULLABLE" },
    { name = "executive_summary", type = "STRING", mode = "NULLABLE" },
    { name = "payload_json", type = "JSON", mode = "REQUIRED" },
    { name = "refreshed_by", type = "STRING", mode = "NULLABLE" },
    { name = "updated_at", type = "TIMESTAMP", mode = "REQUIRED" },
  ])
}

resource "google_bigquery_table" "insights_digest_delivery" {
  dataset_id          = google_bigquery_dataset.marts_insights.dataset_id
  table_id            = "digest_delivery"
  project             = var.project_id
  deletion_protection = false

  description = "Each Digest email/Slack attempt — body + audience for audit"

  time_partitioning {
    type  = "DAY"
    field = "period_date"
  }

  clustering = ["product", "cadence"]

  schema = jsonencode([
    { name = "period_date", type = "DATE", mode = "REQUIRED" },
    { name = "product", type = "STRING", mode = "REQUIRED" },
    { name = "cadence", type = "STRING", mode = "REQUIRED" },
    { name = "channel", type = "STRING", mode = "NULLABLE" },
    { name = "audience", type = "STRING", mode = "NULLABLE" },
    { name = "subject", type = "STRING", mode = "NULLABLE" },
    { name = "body_text", type = "STRING", mode = "NULLABLE" },
    { name = "delivered", type = "BOOL", mode = "NULLABLE" },
    { name = "sent_at", type = "TIMESTAMP", mode = "REQUIRED" },
  ])
}
