output "project_id" {
  value = var.project_id
}

output "region" {
  value = var.region
}

output "api_service_name" {
  value = var.api_service_name
}

output "artifact_registry" {
  value = "${var.region}-docker.pkg.dev/${var.project_id}/${var.api_service_name}"
}

output "frontend_bucket_name" {
  value = google_storage_bucket.frontend.name
}

output "frontend_bucket_url" {
  value = "https://storage.googleapis.com/${google_storage_bucket.frontend.name}/index.html"
}

output "api_url" {
  description = "Default Cloud Run URL — use for VITE_API_URL or as Cloudflare CNAME target for a custom API subdomain."
  value       = google_cloud_run_service.api.status[0].url
}

output "github_actions_sa_email" {
  value = google_service_account.github_actions.email
}

output "github_actions_sa_key_json" {
  value     = base64decode(google_service_account_key.github_actions.private_key)
  sensitive = true
}

output "gemini_secret_id" {
  value = google_secret_manager_secret.gemini_api_key.secret_id
}

output "bq_datasets" {
  description = "Insights BigQuery datasets in cognispace"
  value = {
    raw_billing       = google_bigquery_dataset.raw_billing.dataset_id
    raw_langfuse      = google_bigquery_dataset.raw_langfuse.dataset_id
    marts_growth      = google_bigquery_dataset.marts_growth.dataset_id
    marts_cost        = google_bigquery_dataset.marts_cost.dataset_id
    marts_reliability = google_bigquery_dataset.marts_reliability.dataset_id
    marts_ai          = google_bigquery_dataset.marts_ai.dataset_id
    marts_insights    = google_bigquery_dataset.marts_insights.dataset_id
    snapshot_table    = "${google_bigquery_dataset.marts_insights.dataset_id}.${google_bigquery_table.insights_snapshot_daily.table_id}"
  }
}

output "cloudflare_dns_hint" {
  value = <<-EOT
    Frontend (${var.frontend_domain}):
      Point at bucket ${google_storage_bucket.frontend.name} (same pattern as synthapse.xyz).

    API (europe-central2 — no GCP domain mapping):
      1. Use run.app URL directly: ${google_cloud_run_service.api.status[0].url}
      2. Or in Cloudflare: CNAME ${var.api_domain != "" ? var.api_domain : "api.stateboard.synthapse.xyz"} → host from api_url (strip https://), proxy ON.
      Set GitHub variable STATEBOARD_API_URL or VITE_API_URL to the URL users will call (custom domain or run.app).

    CORS on Cloud Run must include: https://${var.frontend_domain}
  EOT
}
