# Insights Digests M5 — Cloud Scheduler → HTTP Cloud Function
# Deploy the Function first (Narrate/scripts/deploy_digest_fn.sh), then set
# digest_function_url and terraform apply.

resource "google_service_account" "insights_digest_scheduler" {
  count        = var.digest_function_url != "" ? 1 : 0
  account_id   = "insights-digest-scheduler"
  display_name = "Insights Digest Scheduler"
  project      = var.project_id
}

# Allow Scheduler SA to invoke the Function (Cloud Run underlying gen2).
resource "google_cloud_run_service_iam_member" "insights_digest_invoker" {
  count    = var.digest_function_url != "" ? 1 : 0
  project  = var.project_id
  location = var.region
  service  = var.digest_function_name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.insights_digest_scheduler[0].email}"
}

# Daily 06:00 Europe/Warsaw — Langfuse → marts.ai + build_snapshots
resource "google_cloud_scheduler_job" "insights_daily" {
  count            = var.digest_function_url != "" ? 1 : 0
  name             = "insights-daily-pipeline"
  description      = "Langfuse + Clarity + marts + Snapshot build (daily_pipeline)"
  schedule         = "0 6 * * *"
  time_zone        = "Europe/Warsaw"
  attempt_deadline = "480s"
  region           = var.region
  project          = var.project_id

  http_target {
    http_method = "GET"
    uri         = "${trimsuffix(var.digest_function_url, "/")}?action=daily_pipeline&all=1"

    oidc_token {
      service_account_email = google_service_account.insights_digest_scheduler[0].email
      audience              = trimsuffix(var.digest_function_url, "/")
    }
  }

  depends_on = [google_cloud_run_service_iam_member.insights_digest_invoker]
}

# Weekly Monday 07:00 — Digests for all products
resource "google_cloud_scheduler_job" "insights_weekly" {
  count            = var.digest_function_url != "" ? 1 : 0
  name             = "insights-weekly-digest"
  description      = "Weekly Digests for kih, lindle, yca"
  schedule         = "0 7 * * 1"
  time_zone        = "Europe/Warsaw"
  attempt_deadline = "480s"
  region           = var.region
  project          = var.project_id

  http_target {
    http_method = "GET"
    uri         = "${trimsuffix(var.digest_function_url, "/")}?all=1&cadence=weekly"

    oidc_token {
      service_account_email = google_service_account.insights_digest_scheduler[0].email
      audience              = trimsuffix(var.digest_function_url, "/")
    }
  }

  depends_on = [google_cloud_run_service_iam_member.insights_digest_invoker]
}
