#!/usr/bin/env bash
# Deploy Insights Digest Cloud Function (gen2) for M5.
# Loads Narrate/.env into Function env (never prints values).
# Run from repo:  bash Narrate/scripts/deploy_digest_fn.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROJECT="${GCP_PROJECT:-cognispace}"
REGION="${GCP_REGION:-europe-central2}"
FN_NAME="${DIGEST_FN_NAME:-insights-digest}"
RUNTIME="${DIGEST_RUNTIME:-python312}"
ENV_FILE="${ROOT}/.env"

echo "Deploying $FN_NAME to $PROJECT / $REGION (source=$ROOT)"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing $ENV_FILE — copy from .env.example and fill secrets." >&2
  exit 1
fi

# shellcheck disable=SC1090
set -a
# shellcheck disable=SC1091
source "$ENV_FILE"
set +a

# Keys from .env to ship to the Function (skip local-only paths / DB URLs).
# Values are written to a temp YAML — never echoed.
ENV_KEYS=(
  DIGEST_GENAI
  DIGEST_CHANNEL
  DIGEST_EMAIL_TO
  DIGEST_EMAIL_TO_KIH
  DIGEST_EMAIL_TO_LINDLE
  DIGEST_EMAIL_TO_YCA
  BQ_PROJECT
  BQ_LOCATION
  BQ_DATASET_INSIGHTS
  BQ_SNAPSHOT_TABLE
  BQ_STRATEGY_TABLE
  BQ_GA4_LOCATION
  BQ_GA4_LOCATION_KIH
  BQ_GA4_LOCATION_LINDLE
  BQ_GA4_LOCATION_YCA
  BQ_MAX_BYTES_BILLED
  GEMINI_API_KEY
  GEMINI_MODEL
  SMTP_HOST
  SMTP_PORT
  SMTP_USER
  SMTP_PASSWORD
  SMTP_FROM
  LANGFUSE_HOST
  LANGFUSE_PUBLIC_KEY
  LANGFUSE_SECRET_KEY
  LANGFUSE_KIH_PUBLIC_KEY
  LANGFUSE_KIH_SECRET_KEY
  LANGFUSE_LINDLE_PUBLIC_KEY
  LANGFUSE_LINDLE_SECRET_KEY
  LANGFUSE_YCA_PUBLIC_KEY
  LANGFUSE_YCA_SECRET_KEY
  CLARITY_API_TOKEN
  CLARITY_LINDLE_PROJECT_ID
  CLARITY_LINDLE_API_KEY
  CLARITY_YCA_PROJECT_ID
  CLARITY_YCA_API_KEY
  SLACK_WEBHOOK_URL
)

TMP_ENV="$(mktemp -t digest-env.XXXXXX.yaml)"
trap 'rm -f "$TMP_ENV"' EXIT

python3 - "$TMP_ENV" "${ENV_KEYS[@]}" <<'PY'
import json, os, sys

out_path = sys.argv[1]
keys = sys.argv[2:]
lines = [
    "DIGEST_USE_FIXTURE: \"0\"",
    f"BQ_PROJECT: {json.dumps(os.environ.get('BQ_PROJECT') or os.environ.get('GCP_PROJECT') or 'cognispace')}",
    f"BQ_LOCATION: {json.dumps(os.environ.get('BQ_LOCATION') or 'EU')}",
]
seen = {"DIGEST_USE_FIXTURE", "BQ_PROJECT", "BQ_LOCATION"}
for key in keys:
    if key in seen:
        continue
    val = os.environ.get(key)
    if val is None or not str(val).strip():
        continue
    lines.append(f"{key}: {json.dumps(val)}")
    seen.add(key)
with open(out_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print(f"Packed {len(lines)} env vars from .env (values hidden)")
PY

# Explicit AR repo avoids gcloud crash when a prior deploy left dockerRepository unset.
DOCKER_REPO="${DIGEST_DOCKER_REPO:-projects/${PROJECT}/locations/${REGION}/repositories/gcf-artifacts}"

gcloud functions deploy "$FN_NAME" \
  --gen2 \
  --project="$PROJECT" \
  --region="$REGION" \
  --runtime="$RUNTIME" \
  --source="$ROOT" \
  --entry-point=digest_http \
  --trigger-http \
  --allow-unauthenticated \
  --memory=512Mi \
  --timeout=540s \
  --docker-repository="$DOCKER_REPO" \
  --env-vars-file="$TMP_ENV" \
  ${DIGEST_SET_SECRETS:+--set-secrets="$DIGEST_SET_SECRETS"} \
  --quiet

URL="$(gcloud functions describe "$FN_NAME" --gen2 --project="$PROJECT" --region="$REGION" --format='value(serviceConfig.uri)')"
echo "Function URL: $URL"
echo "Daily test:   curl -sS '${URL}?action=daily_pipeline&all=1'"
echo "Weekly test:  curl -sS '${URL}?all=1&cadence=weekly'"
echo "Set terraform var digest_function_url = \"$URL\" then terraform apply"
