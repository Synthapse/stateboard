#!/usr/bin/env bash
# Copy KIH Billing Detailed export (stage on KIH bill) → cognispace hub.
set -euo pipefail

STAGE_PROJECT="${STAGE_PROJECT:-dr-kiwi-app}"
HUB_PROJECT="${HUB_PROJECT:-cognispace}"
DATASET="${DATASET:-raw_billing}"
TABLE="${TABLE:-gcp_billing_export_resource_v1_01BF64_6A600F_517AFE}"

SRC="${STAGE_PROJECT}:${DATASET}.${TABLE}"
DST="${HUB_PROJECT}:${DATASET}.${TABLE}"

echo "Source: ${SRC}"
echo "Dest:   ${DST}"

if ! bq ls --project_id="${STAGE_PROJECT}" "${STAGE_PROJECT}:${DATASET}" 2>/dev/null | grep -q "${TABLE}"; then
  echo "WAIT: source table not created yet (Detailed export can take hours)."
  exit 0
fi

bq mk --dataset --location=EU "${HUB_PROJECT}:${DATASET}" 2>/dev/null || true
bq cp -f "${SRC}" "${DST}"
echo "OK: ${DST}"
