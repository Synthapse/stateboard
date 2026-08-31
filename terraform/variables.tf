variable "project_id" {
  description = "GCP project ID (Synthapse / shared infra project)"
  type        = string
  default     = "cognispace"
}

variable "region" {
  description = "Primary GCP region"
  type        = string
  default     = "europe-central2"
}

variable "api_service_name" {
  description = "Cloud Run service name for the Stateboard API"
  type        = string
  default     = "stateboard-api"
}

variable "frontend_bucket_name" {
  description = "GCS bucket for the static React app (stateboard.synthapse.xyz)"
  type        = string
  default     = "stateboard-synthapse-frontend"
}

variable "gemini_secret_id" {
  description = "Secret Manager secret id for GEMINI_API_KEY"
  type        = string
  default     = "stateboard-gemini-api-key"
}

variable "frontend_domain" {
  description = "Public site hostname (for docs / optional domain mapping)"
  type        = string
  default     = "stateboard.synthapse.xyz"
}

variable "api_domain" {
  description = "Optional friendly API hostname for docs (e.g. api.stateboard.synthapse.xyz). Not created in GCP when region is europe-central2 — use Cloudflare CNAME to api_url instead."
  type        = string
  default     = ""
}

variable "cloud_run_max_instances" {
  description = "Cloud Run max scale"
  type        = string
  default     = "3"
}

variable "github_sa_account_id" {
  description = "Service account id for GitHub Actions deploys"
  type        = string
  default     = "stateboard-github-actions"
}
