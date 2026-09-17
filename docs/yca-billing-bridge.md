# YCA billing → Cognispace hub (bridge)

**Why:** Lindle exports Billing Detailed usage **directly** into `cognispace.raw_billing` because cost project `cognispace` sits on Lindle’s billing account. YCA cannot: Google requires the export **destination project** to be on the **same** billing account, and Cognispace must stay on a **separate** bill.

**Pattern:** YCA billing → BigQuery in a **YCA-billed** project → daily **copy** into Cognispace → Narrate reads hub tables (same as Lindle).

| | Lindle | YCA (this bridge) |
|--|--------|-------------------|
| Billing account | `01C7B7-5B77CD-27EDAD` | `01F545-2E8963-C6EBE1` |
| Native export project | `cognispace` | `adroit-router-462912-n6` (must be on YCA billing) |
| Hub table | `cognispace.raw_billing.gcp_billing_export_resource_v1_01C7B7_5B77CD_27EDAD` | `cognispace.raw_billing.gcp_billing_export_resource_v1_01F545_2E8963_C6EBE1` |
| Who pays export storage | Cognispace bill | **YCA** bill (`adroit-router-462912-n6`) |
| Who pays hub copy + queries | Cognispace | Cognispace |

Narrate expects exactly:  
`gcp_billing_export_resource_v1_` + billing account with `-` → `_`  
(see `Narrate/insights/integrations/products.py` → `billing_export_table_id`).

---

## 1) One-time — stage dataset on YCA (`adroit-router-462912-n6`)

There is **no** GCP project id `yca-ca` — that name is product branding only. Stage project:

**`adroit-router-462912-n6`**

```bash
# Project must appear in YCA Billing → BigQuery export picker
gcloud services enable bigquery.googleapis.com --project=adroit-router-462912-n6

bq mk --dataset --location=EU \
  --description="YCA Cloud Billing Detailed export (stage; synced to cognispace)" \
  adroit-router-462912-n6:raw_billing
```

## 2) One-time — UI export (like Lindle, but destination = stage)

1. Console → **Billing** → account **`01F545-2E8963-C6EBE1`** (YCA)  
2. **Billing export** → **BigQuery export**  
3. Enable **Detailed usage cost**  
4. Project: **`adroit-router-462912-n6`**  
5. Dataset: **`raw_billing`**  
6. Save  

Wait until Google creates:

`adroit-router-462912-n6.raw_billing.gcp_billing_export_resource_v1_01F545_2E8963_C6EBE1`

```bash
bq ls adroit-router-462912-n6:raw_billing
```

## 3) One-time — hub dataset + IAM

```bash
# Hub dataset (Terraform usually already created this)
bq ls cognispace:raw_billing >/dev/null 2>&1 || \
  bq mk --dataset --location=EU cognispace:raw_billing

# Allow Cognispace to read stage (pick the identity that will run the sync)
# Example: your user for a manual test
```

Use **Console → BigQuery → `adroit-router-462912-n6.raw_billing` → Sharing** and add:

- Principal that runs sync in **cognispace** → role **BigQuery Data Viewer**
- On **`cognispace.raw_billing`**: that principal → **BigQuery Data Editor**

## 4) Daily copy → Cognispace (automated)

**Prefer Terraform** (BigQuery Scheduled Query — not Cloud Tasks):

```bash
cd terraform
terraform plan -target=google_bigquery_data_transfer_config.yca_billing_sync
terraform apply -target=google_project_service.bigquerydatatransfer \
  -target=google_service_account.yca_billing_sync \
  -target=google_project_iam_member.yca_billing_sync_job_user \
  -target=google_bigquery_dataset_iam_member.yca_billing_sync_hub_editor \
  -target=google_bigquery_dataset_iam_member.yca_billing_sync_stage_viewer \
  -target=google_service_account_iam_member.yca_billing_transfer_token_creator \
  -target=google_bigquery_data_transfer_config.yca_billing_sync
```

Creates SA `yca-billing-sync@cognispace…`, IAM on hub + stage, schedule **every day 05:00 UTC**.  
Skips until the export table exists (no hard fail).

Manual one-shot:

```bash
./scripts/sync_yca_billing_to_cognispace.sh
```

Or schedule SQL by hand: `scripts/sql/sync_yca_billing_to_cognispace.sql`.

## 5) Read path (unchanged)

Narrate / digests already query:

`cognispace.raw_billing.gcp_billing_export_resource_v1_01F545_2E8963_C6EBE1`

```bash
cd Narrate
DIGEST_USE_FIXTURE=0 BQ_PROJECT=cognispace \
  python -c "from insights import billing_core; print(billing_core())"
```

---

## Checklist

- [ ] `adroit-router-462912-n6` on **YCA** billing — Cognispace **not** linked to YCA  
- [ ] Detailed export ON → `adroit-router-462912-n6.raw_billing`  
- [ ] Table `gcp_billing_export_resource_v1_01F545_2E8963_C6EBE1` exists on stage  
- [ ] Daily COPY into `cognispace.raw_billing` (same table id)  
- [ ] `billing_core` / snapshots see YCA cloud cost  

## Same bridge for KIH (optional)

KIH billing `01BF64-6A600F-517AFE` may need the same pattern if `dr-kiwi-app` cannot export into Cognispace: stage on `dr-kiwi-app`, copy to  
`cognispace.raw_billing.gcp_billing_export_resource_v1_01BF64_6A600F_517AFE`.
