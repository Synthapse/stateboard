#!/usr/bin/env bash
# Copy YCA Billing Detailed export (stage on YCA bill) → cognispace hub.
# Same table id Narrate expects (products.billing_export_table_id).
#
# Usage:
#   ./scripts/sync_yca_billing_to_cognispace.sh
#   STAGE_PROJECT=adroit-router-462912-n6 ./scripts/sync_yca_billing_to_cognispace.sh
set -euo pipefail

STAGE_PROJECT="${STAGE_PROJECT:-adroit-router-462912-n6}"
HUB_PROJECT="${HUB_PROJECT:-cognispace}"
DATASET="${DATASET:-raw_billing}"
# YCA billing account 01F545-2E8963-C6EBE1
TABLE="${TABLE:-gcp_billing_export_resource_v1_01F545_2E8963_C6EBE1}"

SRC="${STAGE_PROJECT}:${DATASET}.${TABLE}"
DST="${HUB_PROJECT}:${DATASET}.${TABLE}"

echo "Source: ${SRC}"
echo "Dest:   ${DST}"

if ! bq ls --project_id="${STAGE_PROJECT}" "${STAGE_PROJECT}:${DATASET}" 2>/dev/null | grep -q "${TABLE}"; then
  echo "WAIT: source table not created yet (Detailed export can take hours)."
  echo "      Re-run later, or rely on the daily BigQuery scheduled query (terraform/yca_billing_sync.tf)."
  exit 0
fi

bq mk --dataset --location=EU "${HUB_PROJECT}:${DATASET}" 2>/dev/null || true

bq cp -f "${SRC}" "${DST}"

echo "OK: ${DST}"
bq show --format=prettyjson "${DST}" | python3 -c '
import json,sys
t=json.load(sys.stdin)
print("numRows:", t.get("numRows"), "numBytes:", t.get("numBytes"))
'
