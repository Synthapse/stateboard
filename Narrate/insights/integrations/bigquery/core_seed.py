"""Seed core dims from product registry + Analytics plan taxonomy/inventory (no DB)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from insights.integrations.bigquery.client import get_bigquery_client
from insights.integrations.bigquery.config import BigQueryConfig
from insights.integrations.products import PRODUCT_SOURCES

# Canonical event taxonomy (Analytics & Insights Plan)
FEATURE_SEEDS = [
    "user_signed_up",
    "user_logged_in",
    "onboarding_started",
    "onboarding_completed",
    "feature_viewed",
    "feature_started",
    "feature_completed",
    "feature_failed",
    "subscription_started",
    "subscription_upgraded",
    "subscription_cancelled",
    "ai_chat_started",
    "ai_message_sent",
    "rag_query",
    "agent_run_started",
    "agent_run_completed",
    "agent_run_failed",
]

# Logical deployables from plan inventory (2026-09-13)
# gcp_service = Billing service.description this deployable rolls into
SERVICE_SEEDS: list[dict[str, str]] = [
    # KIH
    {"id": "kih:dr-kiwi-app", "product": "kih", "name": "dr-kiwi-app", "kind": "cloud_run_service", "gcp_service": "Cloud Run"},
    {"id": "kih:notification-queue-v2", "product": "kih", "name": "notification-queue-v2", "kind": "cloud_tasks_queue", "gcp_service": "Cloud Tasks"},
    {"id": "kih:cds-process-due-notifications", "product": "kih", "name": "cds-process-due-notifications", "kind": "run_job", "gcp_service": "Cloud Run"},
    {"id": "kih:cds-purge-events", "product": "kih", "name": "cds-purge-events", "kind": "run_job", "gcp_service": "Cloud Run"},
    {"id": "kih:cds-send-daily-digest", "product": "kih", "name": "cds-send-daily-digest", "kind": "run_job", "gcp_service": "Cloud Run"},
    {"id": "kih:index-rag", "product": "kih", "name": "index-rag", "kind": "run_job", "gcp_service": "Cloud Run"},
    # Lindle
    {"id": "lindle:lindle-backend", "product": "lindle", "name": "lindle-backend", "kind": "cloud_run_service", "gcp_service": "Cloud Run"},
    {"id": "lindle:lindle-backend-agents", "product": "lindle", "name": "lindle-backend-agents", "kind": "cloud_run_service", "gcp_service": "Cloud Run"},
    {"id": "lindle:procureiq", "product": "lindle", "name": "procureiq", "kind": "cloud_run_service", "gcp_service": "Cloud Run"},
    # YCA
    {"id": "yca:yca-ca-backend", "product": "yca", "name": "yca-ca-backend", "kind": "cloud_run_service", "gcp_service": "Cloud Run"},
    {"id": "yca:yca-ca-backend-2", "product": "yca", "name": "yca-ca-backend-2", "kind": "cloud_run_service", "gcp_service": "Cloud Run"},
    {"id": "yca:yca-ca-auth", "product": "yca", "name": "yca-ca-auth", "kind": "cloud_run_service", "gcp_service": "Cloud Run"},
    {"id": "yca:yca-ca-backend-payment", "product": "yca", "name": "yca-ca-backend-payment", "kind": "cloud_run_service", "gcp_service": "Cloud Run"},
]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _dim_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    now = _now().isoformat()
    out = []
    for r in rows:
        out.append(
            {
                "id": r["id"],
                "product": r.get("product"),
                "name": r.get("name"),
                "attributes_json": json.dumps(r.get("attributes") or {}),
                "valid_from": now,
                "valid_to": None,
                "is_current": True,
                "updated_at": now,
            }
        )
    return out


def _merge_dims(client: Any, table_id: str, rows: list[dict[str, Any]], location: str) -> int:
    if not rows:
        return 0
    from google.cloud import bigquery

    staging_id = f"{table_id}_seed_staging"
    schema = client.get_table(table_id).schema
    # attributes_json is JSON type in BQ — load as string then cast in MERGE if needed
    load_rows = []
    for r in rows:
        load_rows.append(
            {
                **r,
                "attributes_json": json.loads(r["attributes_json"])
                if isinstance(r["attributes_json"], str)
                else r["attributes_json"],
            }
        )
    job = client.load_table_from_json(
        load_rows,
        staging_id,
        job_config=bigquery.LoadJobConfig(
            schema=schema,
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
            source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        ),
    )
    job.result()
    merge_sql = f"""
    MERGE `{table_id}` T
    USING `{staging_id}` S
    ON T.id = S.id
    WHEN MATCHED THEN UPDATE SET
      product = S.product,
      name = S.name,
      attributes_json = S.attributes_json,
      is_current = S.is_current,
      updated_at = S.updated_at
    WHEN NOT MATCHED THEN INSERT
      (id, product, name, attributes_json, valid_from, valid_to, is_current, updated_at)
    VALUES
      (S.id, S.product, S.name, S.attributes_json, S.valid_from, S.valid_to, S.is_current, S.updated_at)
    """
    client.query(merge_sql, location=location).result()
    return len(rows)


def seed_core_dims() -> dict[str, Any]:
    """Upsert dim_product, dim_feature, dim_service."""
    cfg = BigQueryConfig.from_env()
    client = get_bigquery_client(cfg.project)
    project = cfg.project

    products = _dim_rows(
        [
            {
                "id": src.product.value,
                "product": src.product.value,
                "name": src.display_name,
                "attributes": {
                    "ga4_property_id": src.ga4_property_id,
                    "ga4_dataset": src.ga4_dataset,
                    "gcp_project_id": src.gcp_project_id,
                    "billing_account_id": src.billing_account_id,
                    "ux_primary": src.ux_primary,
                },
            }
            for src in PRODUCT_SOURCES.values()
        ]
    )

    features = _dim_rows(
        [
            {
                "id": f"{src.product.value}:feature:{name}",
                "product": src.product.value,
                "name": name,
                "attributes": {
                    "taxonomy": "insights_plan",
                    "status": "planned",
                    "event_name": name,
                },
            }
            for src in PRODUCT_SOURCES.values()
            for name in FEATURE_SEEDS
        ]
    )

    services = _dim_rows(
        [
            {
                "id": s["id"],
                "product": s["product"],
                "name": s["name"],
                "attributes": {
                    "kind": s["kind"],
                    "gcp_service": s.get("gcp_service"),
                    "gcp_service_id": (
                        f"{s['product']}:gcp:{s['gcp_service']}"
                        if s.get("gcp_service")
                        else None
                    ),
                    "source": "inventory",
                },
            }
            for s in SERVICE_SEEDS
        ]
    )

    counts = {
        "dim_product": _merge_dims(
            client, f"{project}.core.dim_product", products, cfg.location
        ),
        "dim_feature": _merge_dims(
            client, f"{project}.core.dim_feature", features, cfg.location
        ),
        "dim_service": _merge_dims(
            client, f"{project}.core.dim_service", services, cfg.location
        ),
    }
    return {"status": "ok", "upserted": counts}
