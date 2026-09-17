"""BigQuery client factory — ADC or GOOGLE_APPLICATION_CREDENTIALS."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import TYPE_CHECKING, Any

from insights.integrations.bigquery.config import BigQueryConfig

if TYPE_CHECKING:
    from google.cloud import bigquery

# Default ~50 GiB dry-run ceiling for Insights jobs (override via BQ_MAX_BYTES_BILLED).
_DEFAULT_MAX_BYTES = 50 * 1024 * 1024 * 1024


@lru_cache(maxsize=4)
def get_bigquery_client(project: str | None = None) -> "bigquery.Client":
    """
    Build a shared BigQuery client.
    Auth order:
      1) BQ_CREDENTIALS_PATH / GOOGLE_APPLICATION_CREDENTIALS (SA JSON)
      2) BQ_GCLOUD_ACCOUNT → gcloud user access token (for dual-account local use)
      3) Application Default Credentials
    """
    from google.cloud import bigquery
    from google.oauth2 import service_account

    cfg = BigQueryConfig.from_env()
    project = (project or cfg.project).strip()
    cred_path = (
        os.getenv("BQ_CREDENTIALS_PATH", "").strip()
        or os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    )

    if cred_path and os.path.isfile(cred_path):
        credentials = service_account.Credentials.from_service_account_file(cred_path)
        return bigquery.Client(project=project, credentials=credentials)

    gcloud_account = os.getenv("BQ_GCLOUD_ACCOUNT", "").strip()
    if gcloud_account:
        credentials = _credentials_from_gcloud_account(gcloud_account)
        if credentials is not None:
            return bigquery.Client(project=project, credentials=credentials)

    return bigquery.Client(project=project)


def _credentials_from_gcloud_account(account: str):
    """Use a logged-in gcloud user for BQ while ADC stays elsewhere (e.g. Cloud SQL proxy)."""
    import subprocess

    from google.oauth2.credentials import Credentials

    try:
        token = subprocess.check_output(
            ["gcloud", "auth", "print-access-token", f"--account={account}"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    if not token:
        return None
    return Credentials(token=token)


def clear_bigquery_client_cache() -> None:
    get_bigquery_client.cache_clear()


def query_job_config(**kwargs: Any) -> "bigquery.QueryJobConfig":
    """QueryJobConfig with a hard bytes-billed cap (fail if scan would exceed)."""
    from google.cloud import bigquery

    raw = os.getenv("BQ_MAX_BYTES_BILLED", "").strip()
    max_bytes = int(raw) if raw else _DEFAULT_MAX_BYTES
    return bigquery.QueryJobConfig(maximum_bytes_billed=max_bytes, **kwargs)
