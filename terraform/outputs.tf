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

output "digest_scheduler" {
  description = "M5 Scheduler jobs (empty until digest_function_url is set)"
  value = var.digest_function_url == "" ? null : {
    daily  = try(google_cloud_scheduler_job.insights_daily[0].name, null)
    weekly = try(google_cloud_scheduler_job.insights_weekly[0].name, null)
    url    = var.digest_function_url
  }
}

output "bq_datasets" {
  description = "Insights BigQuery warehouse in cognispace (Analytics & Insights Plan + Digests)"
  value = {
    raw = {
      for k, d in google_bigquery_dataset.raw : k => d.dataset_id
    }
    ga4_analytics  = [for d in google_bigquery_dataset.raw_ga4 : d.dataset_id]
    staging        = google_bigquery_dataset.staging.dataset_id
    core           = google_bigquery_dataset.core.dataset_id
    marts          = google_bigquery_dataset.marts.dataset_id
    marts_insights = google_bigquery_dataset.marts_insights.dataset_id
    snapshot_table = "${google_bigquery_dataset.marts_insights.dataset_id}.${google_bigquery_table.insights_snapshot_daily.table_id}"
    strategy_table = "${google_bigquery_dataset.marts_insights.dataset_id}.${google_bigquery_table.insights_product_strategy.table_id}"
    staging_tables = sort([for t in google_bigquery_table.staging : t.table_id])
    core_tables    = sort(concat([for t in google_bigquery_table.core_dim : t.table_id], [for t in google_bigquery_table.core_fct : t.table_id]))
    marts_tables   = sort([for t in google_bigquery_table.marts : t.table_id])
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
