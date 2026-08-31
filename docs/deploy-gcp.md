# Deploy Stateboard on GCP (Synthapse)

Stateboard is split like Lindle: **static frontend on GCS** + **.NET API on Cloud Run**, deployed from **GitHub Actions**. DNS stays in **Cloudflare** (same pattern as `synthapse.xyz`).

## Architecture

| Host | Service | Deploy workflow |
|------|---------|-----------------|
| `stateboard.synthapse.xyz` | GCS bucket (React SPA) | `frontend_prod.yml` |
| `api.stateboard.synthapse.xyz` | Cloud Run (`stateboard-api`) | `api_prod.yml` |

The browser calls the API via `VITE_API_URL` (set at frontend build time). CORS on the API allows `https://stateboard.synthapse.xyz`.

## 1. Terraform (once per project)

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit project_id, domains, bucket name

terraform init
terraform apply
```

This creates:

- Artifact Registry repo `stateboard-api`
- GCS bucket for the SPA (website config + public read)
- Cloud Run service skeleton (placeholder image; CI replaces it)
- Secret Manager secret `stateboard-gemini-api-key`
- GitHub Actions service account + IAM

Save the deploy key:

```bash
terraform output -raw github_actions_sa_key_json > stateboard-github-sa.json
```

## 2. GitHub repository settings

**Secrets**

| Secret | Value |
|--------|--------|
| `STATEBOARD_GCP_SA_KEY` | Full JSON from `github_actions_sa_key_json` |
| `GEMINI_API_KEY` | Gemini key (optional; synced to Secret Manager on API deploy) |

**Variables** (Settings → Secrets and variables → Actions → Variables)

| Variable | Example |
|----------|---------|
| `STATEBOARD_GCP_PROJECT_ID` | `cognispace` (default in workflows) |
| `STATEBOARD_GCP_REGION` | `europe-central2` |
| `STATEBOARD_FRONTEND_BUCKET` | `stateboard-synthapse-frontend` |
| `STATEBOARD_FRONTEND_DOMAIN` | `stateboard.synthapse.xyz` |
| `STATEBOARD_API_URL` | After API deploy: `https://….run.app` or `https://api.stateboard.synthapse.xyz` |
| `STATEBOARD_API_SERVICE` | `stateboard-api` |
| `STATEBOARD_GEMINI_SECRET_ID` | `stateboard-gemini-api-key` |

## 3. Cloudflare DNS

**Frontend** (`stateboard.synthapse.xyz`):

- Point at your GCS bucket (same approach as main `synthapse.xyz` site).
- SPA: bucket `not_found_page` is `index.html` so `/stateboard` routes work.

**API** — `europe-central2` does **not** support GCP Cloud Run domain mappings (error 501).

Use one of:

1. **Direct run.app URL** (simplest after first API deploy):
   ```bash
   terraform output api_url
   ```
   Set GitHub variable `STATEBOARD_API_URL` to that URL, re-run frontend workflow.

2. **Custom subdomain via Cloudflare** (no GCP domain mapping):
   - CNAME `api.stateboard.synthapse.xyz` → hostname from `api_url` (without `https://`)
   - Proxy ON (orange cloud)
   - Set `STATEBOARD_API_URL=https://api.stateboard.synthapse.xyz`
   - Re-run frontend workflow so `VITE_API_URL` matches

CORS on Cloud Run is set to `https://stateboard.synthapse.xyz` by the API workflow.

## 4. CI/CD

| Workflow | Trigger | Action |
|----------|---------|--------|
| `terraform_plan.yml` | PR touching `terraform/` | `terraform plan` |
| `api_prod.yml` | Push `main` (API paths) | Build Docker → push GAR → deploy Cloud Run |
| `frontend_prod.yml` | Push `main` (web paths) | `npm run build` → `gsutil rsync` to bucket |

Manual deploy: Actions → workflow → **Run workflow**.

## 5. Local parity

```bash
dotnet run --project src/Stateboard.Api --urls http://127.0.0.1:5281
cd apps/web && npm run dev
```

Production frontend build:

```bash
VITE_API_URL=https://api.stateboard.synthapse.xyz npm run build
```

## 6. Notes

- **No database** — API is stateless; scans clone repos to temp disk.
- **Git** is installed in the API container for `git clone` scans.
- **Fixtures** (`fixtures/sample-terraform`) are baked into the image for the sample endpoint.
- Rotate `STATEBOARD_GCP_SA_KEY` by re-running `terraform apply` (new SA key) and updating the GitHub secret.
