# KIH (Dr Kiwi) billing → Cognispace hub (bridge)

Same reason as YCA: Cognispace is on **Lindle** billing (`01C7B7-…`), so KIH billing
`01BF64-6A600F-517AFE` cannot use Cognispace as the native export destination.

| | Value |
|--|--------|
| Billing account | `01BF64-6A600F-517AFE` |
| Stage project | `dr-kiwi-app` |
| Stage dataset | `raw_billing` (EU) |
| Hub table | `cognispace.raw_billing.gcp_billing_export_resource_v1_01BF64_6A600F_517AFE` |

## Steps

```bash
# 1) Stage dataset
gcloud services enable bigquery.googleapis.com --project=dr-kiwi-app
bq mk --dataset --location=EU \
  --description="KIH Cloud Billing Detailed export (stage; synced to cognispace)" \
  dr-kiwi-app:raw_billing

# 2) UI: Billing → 01BF64-6A600F-517AFE → Detailed usage cost
#    Project: dr-kiwi-app · Dataset: raw_billing · Location: EU

# 3) Terraform sync (reuses DTS from billing_dts.tf)
cd terraform
terraform apply \
  -target=google_service_account.kih_billing_sync \
  -target=google_project_iam_member.kih_billing_sync_job_user \
  -target=google_bigquery_dataset_iam_member.kih_billing_sync_hub_editor \
  -target=google_bigquery_dataset_iam_member.kih_billing_sync_stage_viewer \
  -target=google_service_account_iam_member.kih_billing_transfer_token_creator \
  -target=google_bigquery_data_transfer_config.kih_billing_sync

# Token creator (if apply misses it — same pattern as YCA)
gcloud iam service-accounts add-iam-policy-binding \
  kih-billing-sync@cognispace.iam.gserviceaccount.com \
  --project=cognispace \
  --member="serviceAccount:service-$(gcloud projects describe cognispace --format='value(projectNumber)')@gcp-sa-bigquerydatatransfer.iam.gserviceaccount.com" \
  --role='roles/iam.serviceAccountTokenCreator'

# 4) When stage table exists:
./scripts/sync_kih_billing_to_cognispace.sh
```

Also see [yca-billing-bridge.md](./yca-billing-bridge.md) for the parallel YCA flow.
