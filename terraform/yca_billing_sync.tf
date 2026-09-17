# YCA billing stage (adroit) → Cognispace hub — daily copy.
# DTS API / service identity: billing_dts.tf

variable "yca_billing_sync_enabled" {
  description = "Create SA + daily BQ scheduled query copying YCA billing into cognispace.raw_billing"
  type        = bool
  default     = true
}

variable "yca_billing_stage_project" {
  description = "YCA-billed GCP project that hosts the native Billing Detailed export"
  type        = string
  default     = "adroit-router-462912-n6"
}

variable "yca_billing_stage_dataset" {
  type    = string
  default = "raw_billing"
}

variable "yca_billing_account_id" {
  description = "YCA Cloud Billing account id (hyphenated)"
  type        = string
  default     = "01F545-2E8963-C6EBE1"
}

variable "yca_billing_sync_schedule" {
  description = "BigQuery Data Transfer schedule (UTC). After export lands overnight."
  type        = string
  default     = "every day 05:00"
}

locals {
  yca_billing_table = "gcp_billing_export_resource_v1_${replace(var.yca_billing_account_id, "-", "_")}"
  yca_billing_sync_sql = <<-SQL
    -- Skip quietly until Google creates the export table (can take hours after enabling).
    IF (
      SELECT COUNT(*)
      FROM `${var.yca_billing_stage_project}.${var.yca_billing_stage_dataset}.INFORMATION_SCHEMA.TABLES`
      WHERE table_name = '${local.yca_billing_table}'
    ) > 0
    THEN
      -- DROP + COPY: REPLACE…COPY can miss new ingestion-time partitions;
      -- AS SELECT cannot replace a day-partitioned billing export table.
      DROP TABLE IF EXISTS
        `${var.project_id}.raw_billing.${local.yca_billing_table}`;
      CREATE TABLE
        `${var.project_id}.raw_billing.${local.yca_billing_table}`
      COPY
        `${var.yca_billing_stage_project}.${var.yca_billing_stage_dataset}.${local.yca_billing_table}`;
    END IF;
  SQL
}

resource "google_service_account" "yca_billing_sync" {
  count        = var.yca_billing_sync_enabled ? 1 : 0
  project      = var.project_id
  account_id   = "yca-billing-sync"
  display_name = "YCA billing → Cognispace BQ sync"
}

resource "google_project_iam_member" "yca_billing_sync_job_user" {
  count   = var.yca_billing_sync_enabled ? 1 : 0
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.yca_billing_sync[0].email}"
}

resource "google_bigquery_dataset_iam_member" "yca_billing_sync_hub_editor" {
  count      = var.yca_billing_sync_enabled ? 1 : 0
  project    = var.project_id
  dataset_id = google_bigquery_dataset.raw["raw_billing"].dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.yca_billing_sync[0].email}"
}

resource "google_bigquery_dataset_iam_member" "yca_billing_sync_stage_viewer" {
  count      = var.yca_billing_sync_enabled ? 1 : 0
  project    = var.yca_billing_stage_project
  dataset_id = var.yca_billing_stage_dataset
  role       = "roles/bigquery.dataViewer"
  member     = "serviceAccount:${google_service_account.yca_billing_sync[0].email}"
}

resource "google_service_account_iam_member" "yca_billing_transfer_token_creator" {
  count              = var.yca_billing_sync_enabled ? 1 : 0
  service_account_id = google_service_account.yca_billing_sync[0].name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:${google_project_service_identity.bigquerydatatransfer[0].email}"

  depends_on = [google_project_service_identity.bigquerydatatransfer]
}

resource "google_bigquery_data_transfer_config" "yca_billing_sync" {
  count = var.yca_billing_sync_enabled ? 1 : 0

  project              = var.project_id
  display_name         = "sync-yca-billing-to-cognispace"
  location             = var.bq_location
  data_source_id       = "scheduled_query"
  schedule             = var.yca_billing_sync_schedule
  service_account_name = google_service_account.yca_billing_sync[0].email
  # Do NOT set destination_dataset_id — SQL uses fully-qualified CREATE/COPY targets.

  params = {
    query = local.yca_billing_sync_sql
  }

  depends_on = [
    google_project_service.bigquerydatatransfer,
    google_project_service_identity.bigquerydatatransfer,
    google_service_account_iam_member.yca_billing_transfer_token_creator,
    google_bigquery_dataset_iam_member.yca_billing_sync_hub_editor,
    google_bigquery_dataset_iam_member.yca_billing_sync_stage_viewer,
    google_project_iam_member.yca_billing_sync_job_user,
  ]
}

output "yca_billing_sync" {
  value = var.yca_billing_sync_enabled ? {
    service_account = google_service_account.yca_billing_sync[0].email
    transfer_config = google_bigquery_data_transfer_config.yca_billing_sync[0].name
    schedule        = var.yca_billing_sync_schedule
    stage_table     = "${var.yca_billing_stage_project}.${var.yca_billing_stage_dataset}.${local.yca_billing_table}"
    hub_table       = "${var.project_id}.raw_billing.${local.yca_billing_table}"
  } : null
}
