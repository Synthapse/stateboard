"""Billing export → core.dim_gcp_service + core.fct_gcp_cost + marts.cost."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from insights.integrations.bigquery.client import get_bigquery_client
from insights.integrations.bigquery.config import BigQueryConfig
from insights.integrations.products import (
    BQ_HUB_PROJECT,
    PRODUCT_SOURCES,
    billing_export_table_id,
)


def _product_case_sql() -> str:
    """CASE project.id → product code."""
    whens = []
    for src in PRODUCT_SOURCES.values():
        whens.append(f"WHEN project.id = '{src.gcp_project_id}' THEN '{src.product.value}'")
    return "CASE\n  " + "\n  ".join(whens) + "\n  ELSE NULL\nEND"


def _billing_tables_union() -> str:
    """UNION ALL of known export tables that may exist (fail at query if missing — caller filters)."""
    parts = []
    for src in PRODUCT_SOURCES.values():
        tid = (
            f"`{BQ_HUB_PROJECT}.raw_billing."
            f"{billing_export_table_id(src.billing_account_id)}`"
        )
        parts.append(f"SELECT * FROM {tid}")
    # Prefer single known Lindle table first; multi-table via separate runs
    return parts


def load_billing_core(*, lookback_days: int = 60) -> dict[str, Any]:
    """
    From each product's billing export table (skip 404):
      - MERGE distinct services into core.dim_gcp_service
      - MERGE daily cost into core.fct_gcp_cost
      - Promote marts.cost
    """
    cfg = BigQueryConfig.from_env()
    client = get_bigquery_client(cfg.project)
    now = datetime.now(timezone.utc).isoformat()
    product_expr = _product_case_sql()
    results: list[dict[str, Any]] = []

    for src in PRODUCT_SOURCES.values():
        table = (
            f"{BQ_HUB_PROJECT}.raw_billing."
            f"{billing_export_table_id(src.billing_account_id)}"
        )
        try:
            client.get_table(table)
        except Exception:
            results.append(
                {"product": src.product.value, "status": "skipped_no_billing_table"}
            )
            continue

        # dim_gcp_service — one row per product × GCP service (Python JSON avoids NUMERIC issues)
        svc_sync: dict[str, Any] | None = None
        try:
            dim_q = f"""
            SELECT
              ({product_expr}) AS product,
              service.description AS service_name,
              ANY_VALUE(project.id) AS gcp_project_id,
              CAST(SUM(cost) AS FLOAT64) AS cost_usd_lookback
            FROM `{table}`
            WHERE service.description IS NOT NULL
              AND DATE(usage_start_time) >= DATE_SUB(CURRENT_DATE(), INTERVAL {int(lookback_days)} DAY)
              AND ({product_expr}) IS NOT NULL
            GROUP BY 1, 2
            """
            dim_rows = []
            for r in client.query(dim_q, location=cfg.location).result():
                product = r["product"]
                name = r["service_name"]
                dim_rows.append(
                    {
                        "id": f"{product}:gcp:{name}",
                        "product": product,
                        "name": name,
                        "attributes_json": {
                            "service_description": name,
                            "gcp_project_id": r["gcp_project_id"],
                            "cost_usd_lookback": float(r["cost_usd_lookback"] or 0),
                            "lookback_days": int(lookback_days),
                        },
                        "valid_from": now,
                        "valid_to": None,
                        "is_current": True,
                        "updated_at": now,
                    }
                )
            if dim_rows:
                from google.cloud import bigquery

                dim_table = f"{cfg.project}.core.dim_gcp_service"
                staging = f"{dim_table}_billing_staging"
                dest = client.get_table(dim_table)
                client.load_table_from_json(
                    dim_rows,
                    staging,
                    job_config=bigquery.LoadJobConfig(
                        schema=dest.schema,
                        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
                        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
                    ),
                ).result()
                client.query(
                    f"""
                    MERGE `{dim_table}` T
                    USING `{staging}` S
                    ON T.id = S.id
                    WHEN MATCHED THEN UPDATE SET
                      product = S.product,
                      name = S.name,
                      attributes_json = S.attributes_json,
                      updated_at = S.updated_at,
                      is_current = S.is_current
                    WHEN NOT MATCHED THEN INSERT ROW
                    """,
                    location=cfg.location,
                ).result()
                client.query(
                    f"""
                    DELETE FROM `{dim_table}`
                    WHERE product IS NULL OR STARTS_WITH(id, 'gcp:')
                    """,
                    location=cfg.location,
                ).result()
                svc_sync = _sync_dim_service_with_gcp(client, cfg, dim_rows, now)
            else:
                svc_sync = {"status": "empty"}
        except Exception as exc:
            results.append(
                {
                    "product": src.product.value,
                    "status": "dim_error",
                    "error": str(exc)[:200],
                }
            )
            continue

        # fct_gcp_cost — day × product × service
        fct_staging = f"{cfg.project}.core.fct_gcp_cost_billing_staging"
        fct_sql = f"""
        CREATE OR REPLACE TABLE `{fct_staging}` AS
        SELECT
          TIMESTAMP(DATE(usage_start_time)) AS event_ts,
          ({product_expr}) AS product,
          CONCAT(({product_expr}), ':gcp:', service.description) AS entity_id,
          'cloud_cost' AS metric_name,
          SUM(cost) AS metric_value,
          SUM(cost) AS cost_usd,
          CAST(NULL AS STRING) AS status,
          PARSE_JSON(TO_JSON_STRING(STRUCT(
            service.description AS service_description,
            project.id AS gcp_project_id
          ))) AS props_json,
          TIMESTAMP('{now}') AS updated_at
        FROM `{table}`
        WHERE DATE(usage_start_time) >= DATE_SUB(CURRENT_DATE(), INTERVAL {int(lookback_days)} DAY)
          AND ({product_expr}) IS NOT NULL
        GROUP BY 1, 2, 3, service.description, project.id
        """
        try:
            client.query(fct_sql, location=cfg.location).result()
            client.query(
                f"""
                MERGE `{cfg.project}.core.fct_gcp_cost` T
                USING `{fct_staging}` S
                ON T.product = S.product
                   AND T.event_ts = S.event_ts
                   AND IFNULL(T.entity_id, '') = IFNULL(S.entity_id, '')
                   AND IFNULL(T.metric_name, '') = IFNULL(S.metric_name, '')
                WHEN MATCHED THEN UPDATE SET
                  metric_value = S.metric_value,
                  cost_usd = S.cost_usd,
                  props_json = S.props_json,
                  updated_at = S.updated_at
                WHEN NOT MATCHED THEN INSERT ROW
                """,
                location=cfg.location,
            ).result()
            # Drop legacy entity_id gcp:* (no product prefix)
            client.query(
                f"""
                DELETE FROM `{cfg.project}.core.fct_gcp_cost`
                WHERE STARTS_WITH(entity_id, 'gcp:')
                """,
                location=cfg.location,
            ).result()
        except Exception as exc:
            results.append(
                {
                    "product": src.product.value,
                    "status": "fct_error",
                    "error": str(exc)[:200],
                }
            )
            continue

        results.append(
            {
                "product": src.product.value,
                "status": "ok",
                "table": table,
                "dim_service_sync": svc_sync,
            }
        )

    mart = _promote_marts_cost(client, cfg, lookback_days=lookback_days)
    return {"billing": results, "marts_cost": mart}


def _sync_dim_service_with_gcp(
    client: Any,
    cfg: BigQueryConfig,
    gcp_dim_rows: list[dict[str, Any]],
    now: str,
) -> dict[str, Any]:
    """
    Aggregate gcp services into dim_service:
      1) Upsert each dim_gcp_service as dim_service (kind=gcp_billing_service)
      2) Enrich inventory deployables with gcp_service_id + shared cost_usd_lookback
    """
    from google.cloud import bigquery

    from insights.integrations.bigquery.core_seed import SERVICE_SEEDS

    cost_by_key = {
        (r["product"], r["name"]): float((r.get("attributes_json") or {}).get("cost_usd_lookback") or 0)
        for r in gcp_dim_rows
    }

    rows: list[dict[str, Any]] = []
    # 1) Billing services as first-class dim_service rows
    for r in gcp_dim_rows:
        attrs = dict(r.get("attributes_json") or {})
        attrs.update(
            {
                "kind": "gcp_billing_service",
                "gcp_service_id": r["id"],
                "source": "billing",
            }
        )
        rows.append(
            {
                "id": r["id"],
                "product": r["product"],
                "name": r["name"],
                "attributes_json": attrs,
                "valid_from": now,
                "valid_to": None,
                "is_current": True,
                "updated_at": now,
            }
        )

    # 2) Inventory deployables linked to gcp category (+ cost rollup)
    for s in SERVICE_SEEDS:
        gcp_name = s.get("gcp_service")
        if not gcp_name:
            continue
        product = s["product"]
        gcp_id = f"{product}:gcp:{gcp_name}"
        cost = cost_by_key.get((product, gcp_name))
        rows.append(
            {
                "id": s["id"],
                "product": product,
                "name": s["name"],
                "attributes_json": {
                    "kind": s["kind"],
                    "gcp_service": gcp_name,
                    "gcp_service_id": gcp_id,
                    "cost_usd_lookback": cost,
                    "source": "inventory",
                },
                "valid_from": now,
                "valid_to": None,
                "is_current": True,
                "updated_at": now,
            }
        )

    if not rows:
        return {"status": "empty", "rows": 0}

    table_id = f"{cfg.project}.core.dim_service"
    staging = f"{table_id}_gcp_sync_staging"
    dest = client.get_table(table_id)
    client.load_table_from_json(
        rows,
        staging,
        job_config=bigquery.LoadJobConfig(
            schema=dest.schema,
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
            source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        ),
    ).result()
    client.query(
        f"""
        MERGE `{table_id}` T
        USING `{staging}` S
        ON T.id = S.id
        WHEN MATCHED THEN UPDATE SET
          product = S.product,
          name = S.name,
          attributes_json = S.attributes_json,
          updated_at = S.updated_at,
          is_current = S.is_current
        WHEN NOT MATCHED THEN INSERT ROW
        """,
        location=cfg.location,
    ).result()
    return {"status": "ok", "rows": len(rows)}


def _promote_marts_cost(client: Any, cfg: BigQueryConfig, *, lookback_days: int) -> dict[str, Any]:
    """Aggregate fct_gcp_cost → marts.cost (Python builds JSON to avoid NUMERIC/JSON issues)."""
    from google.cloud import bigquery

    now = datetime.now(timezone.utc).isoformat()
    sql = f"""
    SELECT
      DATE(event_ts) AS period_date,
      product,
      CAST(SUM(cost_usd) AS FLOAT64) AS cloud_cost_usd,
      COUNT(*) AS line_count
    FROM `{cfg.project}.core.fct_gcp_cost`
    WHERE DATE(event_ts) >= DATE_SUB(CURRENT_DATE(), INTERVAL {int(lookback_days)} DAY)
      AND product IS NOT NULL
    GROUP BY 1, 2
    """
    try:
        rows_out = []
        for r in client.query(sql, location=cfg.location).result():
            rows_out.append(
                {
                    "period_date": r["period_date"].isoformat(),
                    "product": r["product"],
                    "cadence": "daily",
                    "metrics_json": {
                        "cloud_cost_usd": float(r["cloud_cost_usd"] or 0),
                        "line_count": int(r["line_count"] or 0),
                    },
                    "updated_at": now,
                }
            )
        if not rows_out:
            return {"status": "ok", "rows_upserted": 0}
        staging = f"{cfg.project}.marts.cost_billing_staging"
        dest = client.get_table(f"{cfg.project}.marts.cost")
        client.load_table_from_json(
            rows_out,
            staging,
            job_config=bigquery.LoadJobConfig(
                schema=dest.schema,
                write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
                source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
            ),
        ).result()
        client.query(
            f"""
            MERGE `{cfg.project}.marts.cost` T
            USING `{staging}` S
            ON T.product = S.product
               AND T.period_date = S.period_date
               AND IFNULL(T.cadence, 'daily') = IFNULL(S.cadence, 'daily')
            WHEN MATCHED THEN UPDATE SET
              metrics_json = S.metrics_json,
              updated_at = S.updated_at
            WHEN NOT MATCHED THEN INSERT (period_date, product, cadence, metrics_json, updated_at)
            VALUES (S.period_date, S.product, S.cadence, S.metrics_json, S.updated_at)
            """,
            location=cfg.location,
        ).result()
        return {"status": "ok", "rows_upserted": len(rows_out)}
    except Exception as exc:
        return {"status": "error", "error": str(exc)[:200]}
