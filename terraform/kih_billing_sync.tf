# KIH (Dr Kiwi) billing stage (dr-kiwi-app) → Cognispace hub — daily copy.
# Same pattern as YCA: Cognispace is on Lindle billing, so KIH cannot export
# Detailed usage cost directly into cognispace.

variable "kih_billing_sync_enabled" {
  description = "Daily BQ scheduled query copying KIH billing into cognispace.raw_billing"
  type        = bool
  default     = true
}

variable "kih_billing_stage_project" {
  description = "KIH-billed GCP project that hosts the native Billing Detailed export"
  type        = string
  default     = "dr-kiwi-app"
}

variable "kih_billing_stage_dataset" {
  type    = string
  default = "raw_billing"
}

variable "kih_billing_account_id" {
  description = "KIH Cloud Billing account id (hyphenated)"
  type        = string
  default     = "01BF64-6A600F-517AFE"
}

variable "kih_billing_sync_schedule" {
  description = "BigQuery Data Transfer schedule (UTC)"
  type        = string
  default     = "every day 05:15"
}

locals {
  kih_billing_table = "gcp_billing_export_resource_v1_${replace(var.kih_billing_account_id, "-", "_")}"
  kih_billing_sync_sql = <<-SQL
    IF (
      SELECT COUNT(*)
      FROM `${var.kih_billing_stage_project}.${var.kih_billing_stage_dataset}.INFORMATION_SCHEMA.TABLES`
      WHERE table_name = '${local.kih_billing_table}'
    ) > 0
    THEN
      CREATE OR REPLACE TABLE
        `${var.project_id}.raw_billing.${local.kih_billing_table}`
      COPY
        `${var.kih_billing_stage_project}.${var.kih_billing_stage_dataset}.${local.kih_billing_table}`;
    END IF;
  SQL
}

resource "google_service_account" "kih_billing_sync" {
  count        = var.kih_billing_sync_enabled ? 1 : 0
  project      = var.project_id
  account_id   = "kih-billing-sync"
  display_name = "KIH billing → Cognispace BQ sync"
}

resource "google_project_iam_member" "kih_billing_sync_job_user" {
  count   = var.kih_billing_sync_enabled ? 1 : 0
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.kih_billing_sync[0].email}"
}

resource "google_bigquery_dataset_iam_member" "kih_billing_sync_hub_editor" {
  count      = var.kih_billing_sync_enabled ? 1 : 0
  project    = var.project_id
  dataset_id = google_bigquery_dataset.raw["raw_billing"].dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.kih_billing_sync[0].email}"
}

resource "google_bigquery_dataset_iam_member" "kih_billing_sync_stage_viewer" {
  count      = var.kih_billing_sync_enabled ? 1 : 0
  project    = var.kih_billing_stage_project
  dataset_id = var.kih_billing_stage_dataset
  role       = "roles/bigquery.dataViewer"
  member     = "serviceAccount:${google_service_account.kih_billing_sync[0].email}"
}

resource "google_service_account_iam_member" "kih_billing_transfer_token_creator" {
  count              = var.kih_billing_sync_enabled ? 1 : 0
  service_account_id = google_service_account.kih_billing_sync[0].name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:${google_project_service_identity.bigquerydatatransfer[0].email}"

  depends_on = [google_project_service_identity.bigquerydatatransfer]
}

resource "google_bigquery_data_transfer_config" "kih_billing_sync" {
  count = var.kih_billing_sync_enabled ? 1 : 0

  project              = var.project_id
  display_name         = "sync-kih-billing-to-cognispace"
  location             = var.bq_location
  data_source_id       = "scheduled_query"
  schedule             = var.kih_billing_sync_schedule
  service_account_name = google_service_account.kih_billing_sync[0].email

  params = {
    query = local.kih_billing_sync_sql
  }

  depends_on = [
    google_project_service.bigquerydatatransfer,
    google_project_service_identity.bigquerydatatransfer,
    google_service_account_iam_member.kih_billing_transfer_token_creator,
    google_bigquery_dataset_iam_member.kih_billing_sync_hub_editor,
    google_bigquery_dataset_iam_member.kih_billing_sync_stage_viewer,
    google_project_iam_member.kih_billing_sync_job_user,
  ]
}

output "kih_billing_sync" {
  value = var.kih_billing_sync_enabled ? {
    service_account = google_service_account.kih_billing_sync[0].email
    transfer_config = google_bigquery_data_transfer_config.kih_billing_sync[0].name
    schedule        = var.kih_billing_sync_schedule
    stage_table     = "${var.kih_billing_stage_project}.${var.kih_billing_stage_dataset}.${local.kih_billing_table}"
    hub_table       = "${var.project_id}.raw_billing.${local.kih_billing_table}"
  } : null
}
