"""Shared helpers: write app extract rows into raw_app + core dims."""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from typing import Any, Iterable

from insights.integrations.bigquery.client import get_bigquery_client
from insights.integrations.bigquery.config import BigQueryConfig


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_raw_and_dims(
    *,
    product: str,
    entity: str,  # user | account
    rows: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    """
    rows: {id, name?, attributes?}
    Writes staging-shaped rows into raw_app (payload_json) and MERGEs core.dim_{entity}.
    """
    cfg = BigQueryConfig.from_env()
    client = get_bigquery_client(cfg.project)
    now = _now()
    today = date.today().isoformat()
    items = list(rows)
    if not items:
        return {"product": product, "entity": entity, "status": "empty", "n": 0}

    raw_rows = []
    dim_rows = []
    for r in items:
        rid = str(r["id"])
        name = r.get("name")
        attrs = r.get("attributes") or {}
        raw_rows.append(
            {
                "source_system": "app",
                "source_table": f"{product}.{entity}",
                "ingest_date": today,
                "product": product,
                "record_id": rid,
                "event_ts": now,
                "payload_json": {"id": rid, "name": name, **attrs},
                "ingested_at": now,
            }
        )
        dim_rows.append(
            {
                "id": f"{product}:{entity}:{rid}",
                "product": product,
                "name": name,
                "attributes_json": attrs,
                "valid_from": now,
                "valid_to": None,
                "is_current": True,
                "updated_at": now,
            }
        )

    from google.cloud import bigquery

    # raw_app — no fixed table schema in TF beyond dataset; use a landing table
    raw_table = f"{cfg.project}.raw_app.entities"
    _ensure_raw_entities(client, raw_table)
    staging_raw = f"{raw_table}_staging"
    client.load_table_from_json(
        raw_rows,
        staging_raw,
        job_config=bigquery.LoadJobConfig(
            schema=client.get_table(raw_table).schema,
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
            source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        ),
    ).result()
    client.query(
        f"""
        MERGE `{raw_table}` T
        USING `{staging_raw}` S
        ON T.product = S.product AND T.record_id = S.record_id AND T.source_table = S.source_table
        WHEN MATCHED THEN UPDATE SET
          payload_json = S.payload_json,
          ingest_date = S.ingest_date,
          ingested_at = S.ingested_at
        WHEN NOT MATCHED THEN INSERT ROW
        """,
        location=cfg.location,
    ).result()

    dim_table = f"{cfg.project}.core.dim_{entity}"
    staging_dim = f"{dim_table}_app_staging"
    client.load_table_from_json(
        dim_rows,
        staging_dim,
        job_config=bigquery.LoadJobConfig(
            schema=client.get_table(dim_table).schema,
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
            source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        ),
    ).result()
    client.query(
        f"""
        MERGE `{dim_table}` T
        USING `{staging_dim}` S
        ON T.id = S.id
        WHEN MATCHED THEN UPDATE SET
          name = S.name,
          attributes_json = S.attributes_json,
          updated_at = S.updated_at,
          is_current = S.is_current
        WHEN NOT MATCHED THEN INSERT ROW
        """,
        location=cfg.location,
    ).result()
    # Drop stale rows for this product (e.g. prior bad table pick)
    client.query(
        f"""
        DELETE FROM `{dim_table}`
        WHERE product = @product
          AND id NOT IN (SELECT id FROM `{staging_dim}`)
        """,
        job_config=bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("product", "STRING", product),
            ]
        ),
        location=cfg.location,
    ).result()

    return {"product": product, "entity": entity, "status": "ok", "n": len(items)}


def _ensure_raw_entities(client: Any, table_id: str) -> None:
    from google.cloud import bigquery

    try:
        client.get_table(table_id)
        return
    except Exception:
        pass
    schema = [
        bigquery.SchemaField("source_system", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("source_table", "STRING"),
        bigquery.SchemaField("ingest_date", "DATE", mode="REQUIRED"),
        bigquery.SchemaField("product", "STRING"),
        bigquery.SchemaField("record_id", "STRING"),
        bigquery.SchemaField("event_ts", "TIMESTAMP"),
        bigquery.SchemaField("payload_json", "JSON", mode="REQUIRED"),
        bigquery.SchemaField("ingested_at", "TIMESTAMP", mode="REQUIRED"),
    ]
    table = bigquery.Table(table_id, schema=schema)
    table.time_partitioning = bigquery.TimePartitioning(
        type_=bigquery.TimePartitioningType.DAY, field="ingest_date"
    )
    client.create_table(table, exists_ok=True)
