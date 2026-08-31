resource "google_artifact_registry_repository" "api" {
  location      = var.region
  repository_id = var.api_service_name
  format        = "DOCKER"
  description   = "Stateboard API container images"
}

resource "google_storage_bucket" "frontend" {
  name                        = var.frontend_bucket_name
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = false

  website {
    main_page_suffix = "index.html"
    not_found_page   = "index.html"
  }

  labels = {
    app        = "stateboard"
    managed_by = "terraform"
  }
}

resource "google_storage_bucket_iam_member" "frontend_public_read" {
  bucket = google_storage_bucket.frontend.name
  role   = "roles/storage.objectViewer"
  member = "allUsers"
}

resource "google_service_account" "github_actions" {
  account_id   = var.github_sa_account_id
  display_name = "Stateboard GitHub Actions deployer"
}

resource "google_service_account_key" "github_actions" {
  service_account_id = google_service_account.github_actions.name
}

resource "google_project_iam_member" "github_run_admin" {
  project = var.project_id
  role    = "roles/run.admin"
  member  = "serviceAccount:${google_service_account.github_actions.email}"
}

resource "google_project_iam_member" "github_artifact_writer" {
  project = var.project_id
  role    = "roles/artifactregistry.writer"
  member  = "serviceAccount:${google_service_account.github_actions.email}"
}

resource "google_project_iam_member" "github_sa_user" {
  project = var.project_id
  role    = "roles/iam.serviceAccountUser"
  member  = "serviceAccount:${google_service_account.github_actions.email}"
}

resource "google_storage_bucket_iam_member" "github_frontend_admin" {
  bucket = google_storage_bucket.frontend.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.github_actions.email}"
}

resource "google_secret_manager_secret" "gemini_api_key" {
  secret_id = var.gemini_secret_id
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_iam_member" "gemini_runtime_accessor" {
  secret_id = google_secret_manager_secret.gemini_api_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${data.google_project.current.number}-compute@developer.gserviceaccount.com"
}

resource "google_project_iam_member" "github_secret_admin" {
  project = var.project_id
  role    = "roles/secretmanager.admin"
  member  = "serviceAccount:${google_service_account.github_actions.email}"
}

resource "google_cloud_run_service" "api" {
  name     = var.api_service_name
  location = var.region

  template {
    metadata {
      annotations = {
        "autoscaling.knative.dev/maxScale" = var.cloud_run_max_instances
      }
    }

    spec {
      timeout_seconds       = 300
      container_concurrency = 80

      containers {
        image = "us-docker.pkg.dev/cloudrun/container/hello"

        ports {
          container_port = 8080
        }

        resources {
          limits = {
            memory = "512Mi"
            cpu    = "1"
          }
        }
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  lifecycle {
    ignore_changes = [
      template[0].spec[0].containers[0].image,
      template[0].spec[0].containers[0].env,
      template[0].metadata[0].annotations,
    ]
  }

  depends_on = [google_artifact_registry_repository.api]
}

resource "google_cloud_run_service_iam_member" "api_public_invoker" {
  service  = google_cloud_run_service.api.name
  location = google_cloud_run_service.api.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Custom domains via google_cloud_run_domain_mapping are NOT available in europe-central2.
# Use the run.app URL from output api_url, or point Cloudflare CNAME api.* at that host.
