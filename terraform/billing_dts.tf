# Shared BigQuery Data Transfer enablement for product billing → cognispace bridges.
# Used by yca_billing_sync.tf and kih_billing_sync.tf.

locals {
  billing_bridge_enabled = var.yca_billing_sync_enabled || var.kih_billing_sync_enabled
}

resource "google_project_service" "bigquerydatatransfer" {
  count              = local.billing_bridge_enabled ? 1 : 0
  project            = var.project_id
  service            = "bigquerydatatransfer.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service_identity" "bigquerydatatransfer" {
  count    = local.billing_bridge_enabled ? 1 : 0
  provider = google-beta
  project  = var.project_id
  service  = "bigquerydatatransfer.googleapis.com"

  depends_on = [google_project_service.bigquerydatatransfer]
}
