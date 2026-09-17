"""raw_langfuse.daily_metrics → core.fct_llm_traces + core.dim_model."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from insights.integrations.bigquery.client import get_bigquery_client
from insights.integrations.bigquery.config import BigQueryConfig

RAW = "raw_langfuse.daily_metrics"


def load_langfuse_core(*, lookback_days: int = 30) -> dict[str, Any]:
    cfg = BigQueryConfig.from_env()
    client = get_bigquery_client(cfg.project)
    now = datetime.now(timezone.utc).isoformat()
    raw_id = f"{cfg.project}.{RAW}"

    # dim_model — one stub per product Langfuse project (model detail needs richer API later)
    dim_staging = f"{cfg.project}.core.dim_model_lf_staging"
    dim_sql = f"""
    CREATE OR REPLACE TABLE `{dim_staging}` AS
    SELECT
      CONCAT('langfuse:', IFNULL(langfuse_project_id, product)) AS id,
      product,
      IFNULL(langfuse_project_name, product) AS name,
      PARSE_JSON(TO_JSON_STRING(STRUCT(
        langfuse_project_id,
        langfuse_project_name,
        'langfuse' AS source
      ))) AS attributes_json,
      TIMESTAMP('{now}') AS valid_from,
      CAST(NULL AS TIMESTAMP) AS valid_to,
      TRUE AS is_current,
      TIMESTAMP('{now}') AS updated_at
    FROM `{raw_id}`
    WHERE period_date >= DATE_SUB(CURRENT_DATE(), INTERVAL {int(lookback_days)} DAY)
    GROUP BY product, langfuse_project_id, langfuse_project_name
    """
    client.query(dim_sql, location=cfg.location).result()
    client.query(
        f"""
        MERGE `{cfg.project}.core.dim_model` T
        USING `{dim_staging}` S
        ON T.id = S.id
        WHEN MATCHED THEN UPDATE SET
          name = S.name,
          attributes_json = S.attributes_json,
          updated_at = S.updated_at
        WHEN NOT MATCHED THEN INSERT ROW
        """,
        location=cfg.location,
    ).result()

    # fct_llm_traces — daily grain from ETL
    fct_staging = f"{cfg.project}.core.fct_llm_traces_lf_staging"
    fct_sql = f"""
    CREATE OR REPLACE TABLE `{fct_staging}` AS
    SELECT
      TIMESTAMP(period_date) AS event_ts,
      product,
      CONCAT('langfuse:', IFNULL(langfuse_project_id, product)) AS entity_id,
      'llm_daily' AS metric_name,
      CAST(trace_count AS FLOAT64) AS metric_value,
      total_cost_usd AS cost_usd,
      source AS status,
      PARSE_JSON(TO_JSON_STRING(STRUCT(
        trace_count,
        total_cost_usd,
        langfuse_project_id,
        langfuse_project_name
      ))) AS props_json,
      TIMESTAMP('{now}') AS updated_at
    FROM `{raw_id}`
    WHERE period_date >= DATE_SUB(CURRENT_DATE(), INTERVAL {int(lookback_days)} DAY)
    """
    client.query(fct_sql, location=cfg.location).result()
    client.query(
        f"""
        MERGE `{cfg.project}.core.fct_llm_traces` T
        USING `{fct_staging}` S
        ON T.product = S.product
           AND T.event_ts = S.event_ts
           AND IFNULL(T.metric_name, '') = IFNULL(S.metric_name, '')
        WHEN MATCHED THEN UPDATE SET
          metric_value = S.metric_value,
          cost_usd = S.cost_usd,
          entity_id = S.entity_id,
          status = S.status,
          props_json = S.props_json,
          updated_at = S.updated_at
        WHEN NOT MATCHED THEN INSERT ROW
        """,
        location=cfg.location,
    ).result()

    n_dim = list(
        client.query(f"SELECT COUNT(*) AS n FROM `{dim_staging}`", location=cfg.location).result()
    )[0]["n"]
    n_fct = list(
        client.query(f"SELECT COUNT(*) AS n FROM `{fct_staging}`", location=cfg.location).result()
    )[0]["n"]
    return {
        "status": "ok",
        "dim_model_rows": int(n_dim),
        "fct_llm_traces_rows": int(n_fct),
        "lookback_days": lookback_days,
    }
