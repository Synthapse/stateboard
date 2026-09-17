"""Promote Langfuse daily metrics → marts.ai (BI mart)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from insights.integrations.bigquery.client import get_bigquery_client
from insights.integrations.bigquery.config import BigQueryConfig

RAW_TABLE = "raw_langfuse.daily_metrics"
MARTS_AI_TABLE = "marts.ai"


def promote_marts_ai(
    *,
    product: str | None = None,
    lookback_days: int = 7,
) -> dict[str, Any]:
    """
    MERGE raw_langfuse.daily_metrics into marts.ai for the last lookback_days.
    metrics_json = { total_cost_usd, trace_count, langfuse_project_id, source }.
    """
    cfg = BigQueryConfig.from_env()
    client = get_bigquery_client(cfg.project)
    raw_id = f"{cfg.project}.{RAW_TABLE}"
    mart_id = f"{cfg.project}.{MARTS_AI_TABLE}"
    now = datetime.now(timezone.utc).isoformat()

    product_filter = f"AND product = @product" if product else ""
    params = []
    if product:
        from google.cloud import bigquery

        params.append(bigquery.ScalarQueryParameter("product", "STRING", product))

    # Staging via SELECT … then MERGE (no streaming).
    staging_id = f"{mart_id}_langfuse_staging"
    build_sql = f"""
    CREATE OR REPLACE TABLE `{staging_id}` AS
    SELECT
      period_date,
      product,
      'daily' AS cadence,
      PARSE_JSON(TO_JSON_STRING(STRUCT(
        total_cost_usd,
        trace_count,
        langfuse_project_id,
        langfuse_project_name,
        source AS langfuse_source
      ))) AS metrics_json,
      TIMESTAMP('{now}') AS updated_at
    FROM `{raw_id}`
    WHERE period_date >= DATE_SUB(CURRENT_DATE(), INTERVAL {int(lookback_days)} DAY)
      {product_filter}
    """
    job_config = None
    if params:
        from google.cloud import bigquery

        job_config = bigquery.QueryJobConfig(query_parameters=params)

    client.query(build_sql, job_config=job_config, location=cfg.location).result()

    merge_sql = f"""
    MERGE `{mart_id}` T
    USING `{staging_id}` S
    ON T.product = S.product
       AND T.period_date = S.period_date
       AND IFNULL(T.cadence, 'daily') = IFNULL(S.cadence, 'daily')
    WHEN MATCHED THEN UPDATE SET
      metrics_json = S.metrics_json,
      updated_at = S.updated_at
    WHEN NOT MATCHED THEN INSERT (period_date, product, cadence, metrics_json, updated_at)
    VALUES (S.period_date, S.product, S.cadence, S.metrics_json, S.updated_at)
    """
    client.query(merge_sql, location=cfg.location).result()

    count_sql = f"SELECT COUNT(*) AS n FROM `{staging_id}`"
    n = list(client.query(count_sql, location=cfg.location).result())[0]["n"]
    return {"table": mart_id, "rows_upserted": int(n), "lookback_days": lookback_days}
