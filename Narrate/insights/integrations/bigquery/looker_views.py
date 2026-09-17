"""Create Looker Studio–friendly flat views over marts.* JSON blobs."""

from __future__ import annotations

from typing import Any

from insights.integrations.bigquery.client import get_bigquery_client
from insights.integrations.bigquery.config import BigQueryConfig

# Typed columns Looker can chart without JSON extraction in the UI.
LOOKER_VIEWS: dict[str, str] = {
    "looker_growth": """
    CREATE OR REPLACE VIEW `{project}.marts.looker_growth` AS
    SELECT
      period_date,
      product,
      cadence,
      SAFE_CAST(JSON_VALUE(metrics_json, '$.sessions') AS FLOAT64) AS sessions,
      SAFE_CAST(JSON_VALUE(metrics_json, '$.users') AS FLOAT64) AS users,
      SAFE_CAST(JSON_VALUE(metrics_json, '$.sessions_delta_pct') AS FLOAT64) AS sessions_delta_pct,
      JSON_VALUE(metrics_json, '$.source') AS source,
      updated_at
    FROM `{project}.marts.growth`
    """,
    "looker_product": """
    CREATE OR REPLACE VIEW `{project}.marts.looker_product` AS
    SELECT
      period_date,
      product,
      cadence,
      SAFE_CAST(JSON_VALUE(metrics_json, '$.event_total') AS FLOAT64) AS event_total,
      SAFE_CAST(JSON_VALUE(metrics_json, '$.event_types') AS INT64) AS event_types,
      JSON_VALUE(metrics_json, '$.top_events[0].event_name') AS top_event_name,
      SAFE_CAST(JSON_VALUE(metrics_json, '$.top_events[0].event_count') AS FLOAT64) AS top_event_count,
      JSON_VALUE(metrics_json, '$.source') AS source,
      updated_at
    FROM `{project}.marts.product`
    """,
    "looker_customer": """
    CREATE OR REPLACE VIEW `{project}.marts.looker_customer` AS
    SELECT
      period_date,
      product,
      cadence,
      SAFE_CAST(JSON_VALUE(metrics_json, '$.dau') AS FLOAT64) AS dau,
      SAFE_CAST(JSON_VALUE(metrics_json, '$.sessions') AS FLOAT64) AS sessions,
      SAFE_CAST(JSON_VALUE(metrics_json, '$.wau_engagement_sum') AS FLOAT64) AS wau_engagement_sum,
      SAFE_CAST(JSON_VALUE(metrics_json, '$.active_days_7d') AS INT64) AS active_days_7d,
      JSON_VALUE(metrics_json, '$.source') AS source,
      updated_at
    FROM `{project}.marts.customer`
    """,
    "looker_ai": """
    CREATE OR REPLACE VIEW `{project}.marts.looker_ai` AS
    SELECT
      period_date,
      product,
      cadence,
      SAFE_CAST(JSON_VALUE(metrics_json, '$.total_cost_usd') AS FLOAT64) AS total_cost_usd,
      SAFE_CAST(JSON_VALUE(metrics_json, '$.trace_count') AS FLOAT64) AS trace_count,
      JSON_VALUE(metrics_json, '$.langfuse_project_id') AS langfuse_project_id,
      JSON_VALUE(metrics_json, '$.source') AS source,
      updated_at
    FROM `{project}.marts.ai`
    """,
    "looker_cost": """
    CREATE OR REPLACE VIEW `{project}.marts.looker_cost` AS
    SELECT
      period_date,
      product,
      cadence,
      SAFE_CAST(JSON_VALUE(metrics_json, '$.cloud_cost_usd') AS FLOAT64) AS cloud_cost_usd,
      SAFE_CAST(JSON_VALUE(metrics_json, '$.line_count') AS INT64) AS line_count,
      updated_at
    FROM `{project}.marts.cost`
    """,
    "looker_reliability": """
    CREATE OR REPLACE VIEW `{project}.marts.looker_reliability` AS
    SELECT
      period_date,
      product,
      cadence,
      SAFE_CAST(JSON_VALUE(metrics_json, '$.services_total') AS INT64) AS services_total,
      SAFE_CAST(JSON_VALUE(metrics_json, '$.services_up') AS INT64) AS services_up,
      SAFE_CAST(JSON_VALUE(metrics_json, '$.services_down') AS INT64) AS services_down,
      SAFE_CAST(JSON_VALUE(metrics_json, '$.avg_latency_ms') AS FLOAT64) AS avg_latency_ms,
      SAFE_CAST(JSON_VALUE(metrics_json, '$.exception_count') AS INT64) AS exception_count,
      ARRAY_TO_STRING(
        ARRAY(
          SELECT JSON_VALUE(f)
          FROM UNNEST(JSON_QUERY_ARRAY(metrics_json, '$.failing')) AS f
        ),
        ', '
      ) AS failing_services,
      updated_at
    FROM `{project}.marts.reliability`
    """,
    "looker_feature": """
    CREATE OR REPLACE VIEW `{project}.marts.looker_feature` AS
    SELECT
      DATE(e.event_ts) AS period_date,
      e.product,
      JSON_VALUE(e.props_json, '$.event_name') AS feature_name,
      e.entity_id AS feature_id,
      e.metric_value AS event_count,
      SAFE_CAST(JSON_VALUE(e.props_json, '$.users') AS INT64) AS users,
      JSON_VALUE(d.attributes_json, '$.status') AS feature_status,
      SAFE_CAST(JSON_VALUE(d.attributes_json, '$.event_count_lookback') AS FLOAT64)
        AS event_count_lookback,
      e.updated_at
    FROM `{project}.core.fct_events` e
    LEFT JOIN `{project}.core.dim_feature` d
      ON d.id = e.entity_id
    WHERE e.metric_name = 'event_count'
    """,
    "looker_gcp_service": """
    CREATE OR REPLACE VIEW `{project}.marts.looker_gcp_service` AS
    SELECT
      DATE(f.event_ts) AS period_date,
      f.product,
      JSON_VALUE(f.props_json, '$.service_description') AS service_name,
      f.entity_id AS gcp_service_id,
      f.cost_usd,
      f.metric_value,
      JSON_VALUE(d.attributes_json, '$.gcp_project_id') AS gcp_project_id,
      SAFE_CAST(JSON_VALUE(d.attributes_json, '$.cost_usd_lookback') AS FLOAT64)
        AS cost_usd_lookback,
      f.updated_at
    FROM `{project}.core.fct_gcp_cost` f
    LEFT JOIN `{project}.core.dim_gcp_service` d
      ON d.id = f.entity_id
    WHERE f.metric_name = 'cloud_cost'
    """,
    "looker_service": """
    CREATE OR REPLACE VIEW `{project}.marts.looker_service` AS
    SELECT
      s.id AS service_id,
      s.product,
      s.name AS service_name,
      JSON_VALUE(s.attributes_json, '$.kind') AS kind,
      JSON_VALUE(s.attributes_json, '$.source') AS source,
      JSON_VALUE(s.attributes_json, '$.gcp_service') AS gcp_service,
      JSON_VALUE(s.attributes_json, '$.gcp_service_id') AS gcp_service_id,
      SAFE_CAST(JSON_VALUE(s.attributes_json, '$.cost_usd_lookback') AS FLOAT64)
        AS cost_usd_lookback,
      SAFE_CAST(JSON_VALUE(g.attributes_json, '$.cost_usd_lookback') AS FLOAT64)
        AS gcp_cost_usd_lookback,
      s.updated_at
    FROM `{project}.core.dim_service` s
    LEFT JOIN `{project}.core.dim_gcp_service` g
      ON g.id = JSON_VALUE(s.attributes_json, '$.gcp_service_id')
         OR g.id = s.id
    """,
    "looker_executive": """
    CREATE OR REPLACE VIEW `{project}.marts.looker_executive` AS
    SELECT
      period_date,
      product,
      cadence,
      JSON_VALUE(metrics_json, '$.executive_summary') AS executive_summary,
      JSON_VALUE(metrics_json, '$.direction') AS direction,
      JSON_VALUE(metrics_json, '$.source') AS source,
      JSON_VALUE(metrics_json, '$.priorities[0].product') AS top_priority_product,
      JSON_VALUE(metrics_json, '$.priorities[0].action') AS top_priority_action,
      JSON_VALUE(metrics_json, '$.risks[0]') AS top_risk,
      updated_at
    FROM `{project}.marts.executive`
    """,
}


def ensure_looker_views() -> dict[str, Any]:
    """CREATE OR REPLACE flat views for Looker Studio."""
    cfg = BigQueryConfig.from_env()
    client = get_bigquery_client(cfg.project)
    created: list[str] = []
    errors: list[dict[str, str]] = []
    for name, sql_tmpl in LOOKER_VIEWS.items():
        sql = sql_tmpl.format(project=cfg.project)
        try:
            client.query(sql, location=cfg.location).result()
            created.append(f"{cfg.project}.marts.{name}")
        except Exception as exc:
            errors.append({"view": name, "error": str(exc)[:250]})
    return {
        "status": "ok" if not errors else "partial",
        "views": created,
        "errors": errors,
    }
