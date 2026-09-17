"""GA4 events_* → core.fct_events / fct_sessions → marts.product / growth / customer."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from insights.domain.models import Product
from insights.integrations.bigquery.client import get_bigquery_client
from insights.integrations.bigquery.config import BigQueryConfig
from insights.integrations.products import BQ_HUB_PROJECT, PRODUCT_SOURCES, get_sources

_SQL_DIR = Path(__file__).parent / "sql"


def _load_sql(name: str, **repl: str | int) -> str:
    text = (_SQL_DIR / name).read_text()
    for key, val in repl.items():
        text = text.replace("{{" + key + "}}", str(val))
    return text


def load_ga4_core(
    product: Product | str | None = None,
    *,
    lookback_days: int = 14,
) -> dict[str, Any]:
    """
    Per product (GA4 location may differ from hub EU):
      - daily sessions/users → core.fct_sessions
      - daily event_name counts → core.fct_events
      - promote marts.growth / product / customer
    """
    cfg = BigQueryConfig.from_env()
    client = get_bigquery_client(cfg.project)
    now = datetime.now(timezone.utc).isoformat()
    products = [Product(product)] if product else list(Product)
    results: list[dict[str, Any]] = []

    session_fct: list[dict[str, Any]] = []
    event_fct: list[dict[str, Any]] = []

    for p in products:
        sources = get_sources(p)
        ga4_events = f"{BQ_HUB_PROJECT}.{sources.ga4_dataset}.events_*"
        try:
            sess_sql = _load_sql(
                "ga4_daily_sessions.sql",
                ga4_events=ga4_events,
                lookback_days=int(lookback_days),
                product=p.value,
            )
            sess_rows = list(
                client.query(sess_sql, location=sources.ga4_location).result()
            )
            for r in sess_rows:
                period = r["period_date"]
                ts = datetime(period.year, period.month, period.day, tzinfo=timezone.utc).isoformat()
                sessions = float(r["sessions"] or 0)
                users = float(r["users"] or 0)
                session_fct.append(
                    {
                        "event_ts": ts,
                        "product": p.value,
                        "entity_id": f"{p.value}:sessions",
                        "metric_name": "sessions",
                        "metric_value": sessions,
                        "cost_usd": None,
                        "status": None,
                        "props_json": {"users": users, "source": "ga4"},
                        "updated_at": now,
                    }
                )
                session_fct.append(
                    {
                        "event_ts": ts,
                        "product": p.value,
                        "entity_id": f"{p.value}:users",
                        "metric_name": "users",
                        "metric_value": users,
                        "cost_usd": None,
                        "status": None,
                        "props_json": {"sessions": sessions, "source": "ga4"},
                        "updated_at": now,
                    }
                )

            evt_sql = _load_sql(
                "ga4_daily_events.sql",
                ga4_events=ga4_events,
                lookback_days=int(lookback_days),
                product=p.value,
            )
            evt_rows = list(
                client.query(evt_sql, location=sources.ga4_location).result()
            )
            for r in evt_rows:
                period = r["period_date"]
                ts = datetime(period.year, period.month, period.day, tzinfo=timezone.utc).isoformat()
                event_name = r["event_name"]
                event_fct.append(
                    {
                        "event_ts": ts,
                        "product": p.value,
                        "entity_id": f"{p.value}:feature:{event_name}",
                        "metric_name": "event_count",
                        "metric_value": float(r["event_count"] or 0),
                        "cost_usd": None,
                        "status": None,
                        "props_json": {
                            "event_name": event_name,
                            "users": int(r["users"] or 0),
                            "source": "ga4",
                        },
                        "updated_at": now,
                    }
                )

            results.append(
                {
                    "product": p.value,
                    "status": "ok",
                    "session_days": len(sess_rows),
                    "event_rows": len(evt_rows),
                    "ga4_dataset": sources.ga4_dataset,
                    "ga4_location": sources.ga4_location,
                }
            )
        except Exception as exc:
            results.append(
                {
                    "product": p.value,
                    "status": "error",
                    "error": str(exc)[:300],
                    "ga4_dataset": sources.ga4_dataset,
                }
            )

    sess_merge = _merge_fct(client, cfg, f"{cfg.project}.core.fct_sessions", session_fct)
    evt_merge = _merge_fct(client, cfg, f"{cfg.project}.core.fct_events", event_fct)
    features = _upsert_dim_features(client, cfg, lookback_days=lookback_days)
    marts = _promote_ga4_marts(client, cfg, lookback_days=lookback_days)

    return {
        "ga4": results,
        "fct_sessions": sess_merge,
        "fct_events": evt_merge,
        "dim_feature": features,
        "marts": marts,
    }


def _merge_fct(
    client: Any,
    cfg: BigQueryConfig,
    table_id: str,
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    if not rows:
        return {"status": "empty", "rows": 0}
    from google.cloud import bigquery

    staging = f"{table_id}_ga4_staging"
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
        ON T.product = S.product
           AND T.event_ts = S.event_ts
           AND IFNULL(T.entity_id, '') = IFNULL(S.entity_id, '')
           AND IFNULL(T.metric_name, '') = IFNULL(S.metric_name, '')
        WHEN MATCHED THEN UPDATE SET
          metric_value = S.metric_value,
          props_json = S.props_json,
          updated_at = S.updated_at
        WHEN NOT MATCHED THEN INSERT ROW
        """,
        location=cfg.location,
    ).result()
    return {"status": "ok", "rows": len(rows)}


def _upsert_dim_features(
    client: Any,
    cfg: BigQueryConfig,
    *,
    lookback_days: int,
) -> dict[str, Any]:
    """
    Upsert core.dim_feature from GA4 fct_events: one row per product × event_name
    with usage in attributes_json (event_count / users over lookback).
    """
    from google.cloud import bigquery

    now = datetime.now(timezone.utc).isoformat()
    sql = f"""
    SELECT
      product,
      JSON_VALUE(props_json, '$.event_name') AS event_name,
      SUM(metric_value) AS event_count,
      SUM(SAFE_CAST(JSON_VALUE(props_json, '$.users') AS INT64)) AS users_sum,
      MAX(DATE(event_ts)) AS last_seen
    FROM `{cfg.project}.core.fct_events`
    WHERE DATE(event_ts) >= DATE_SUB(CURRENT_DATE(), INTERVAL {int(lookback_days)} DAY)
      AND metric_name = 'event_count'
      AND JSON_VALUE(props_json, '$.event_name') IS NOT NULL
    GROUP BY 1, 2
    """
    rows = []
    for r in client.query(sql, location=cfg.location).result():
        event_name = r["event_name"]
        product = r["product"]
        rows.append(
            {
                "id": f"{product}:feature:{event_name}",
                "product": product,
                "name": event_name,
                "attributes_json": {
                    "event_name": event_name,
                    "source": "ga4",
                    "status": "observed",
                    "event_count_lookback": float(r["event_count"] or 0),
                    "users_lookback_sum": int(r["users_sum"] or 0),
                    "lookback_days": int(lookback_days),
                    "last_seen": r["last_seen"].isoformat() if r["last_seen"] else None,
                },
                "valid_from": now,
                "valid_to": None,
                "is_current": True,
                "updated_at": now,
            }
        )

    if not rows:
        return {"status": "empty", "rows": 0}

    table_id = f"{cfg.project}.core.dim_feature"
    staging = f"{table_id}_ga4_staging"
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
          is_current = S.is_current,
          updated_at = S.updated_at
        WHEN NOT MATCHED THEN INSERT ROW
        """,
        location=cfg.location,
    ).result()
    # Drop legacy global seeds (product IS NULL / id feature:*)
    client.query(
        f"""
        DELETE FROM `{table_id}`
        WHERE product IS NULL OR STARTS_WITH(id, 'feature:')
        """,
        location=cfg.location,
    ).result()
    return {"status": "ok", "rows": len(rows)}


def _promote_ga4_marts(
    client: Any,
    cfg: BigQueryConfig,
    *,
    lookback_days: int,
) -> dict[str, Any]:
    """Build marts.growth / product / customer from fct_sessions + fct_events."""
    from google.cloud import bigquery

    now = datetime.now(timezone.utc).isoformat()

    # --- growth: sessions + users per day ---
    growth_sql = f"""
    SELECT
      DATE(event_ts) AS period_date,
      product,
      MAX(IF(metric_name = 'sessions', metric_value, NULL)) AS sessions,
      MAX(IF(metric_name = 'users', metric_value, NULL)) AS users
    FROM `{cfg.project}.core.fct_sessions`
    WHERE DATE(event_ts) >= DATE_SUB(CURRENT_DATE(), INTERVAL {int(lookback_days)} DAY)
      AND metric_name IN ('sessions', 'users')
    GROUP BY 1, 2
    ORDER BY 1, 2
    """
    growth_rows: list[dict[str, Any]] = []
    by_product_days: dict[str, list[dict[str, Any]]] = {}
    for r in client.query(growth_sql, location=cfg.location).result():
        item = {
            "period_date": r["period_date"],
            "product": r["product"],
            "sessions": float(r["sessions"] or 0),
            "users": float(r["users"] or 0),
        }
        by_product_days.setdefault(r["product"], []).append(item)
        growth_rows.append(item)

    # WoW / prior-day delta within loaded window
    growth_out = []
    for product, days in by_product_days.items():
        days_sorted = sorted(days, key=lambda x: x["period_date"])
        prev_sess = None
        for d in days_sorted:
            sess = d["sessions"]
            users = d["users"]
            delta = None
            if prev_sess is not None and prev_sess != 0:
                delta = round((sess - prev_sess) / prev_sess * 100.0, 2)
            growth_out.append(
                {
                    "period_date": d["period_date"].isoformat(),
                    "product": product,
                    "cadence": "daily",
                    "metrics_json": {
                        "sessions": sess,
                        "users": users,
                        "sessions_delta_pct": delta,
                        "source": "ga4",
                    },
                    "updated_at": now,
                }
            )
            prev_sess = sess

    # --- product: top events + totals per day ---
    product_sql = f"""
    SELECT
      DATE(event_ts) AS period_date,
      product,
      JSON_VALUE(props_json, '$.event_name') AS event_name,
      metric_value AS event_count,
      SAFE_CAST(JSON_VALUE(props_json, '$.users') AS INT64) AS users
    FROM `{cfg.project}.core.fct_events`
    WHERE DATE(event_ts) >= DATE_SUB(CURRENT_DATE(), INTERVAL {int(lookback_days)} DAY)
      AND metric_name = 'event_count'
    """
    events_by_day: dict[tuple[str, Any], list[dict[str, Any]]] = {}
    for r in client.query(product_sql, location=cfg.location).result():
        key = (r["product"], r["period_date"])
        events_by_day.setdefault(key, []).append(
            {
                "event_name": r["event_name"],
                "event_count": float(r["event_count"] or 0),
                "users": int(r["users"] or 0),
            }
        )

    product_out = []
    for (product, period_date), evts in events_by_day.items():
        evts_sorted = sorted(evts, key=lambda e: e["event_count"], reverse=True)
        total = sum(e["event_count"] for e in evts_sorted)
        top = evts_sorted[:10]
        product_out.append(
            {
                "period_date": period_date.isoformat(),
                "product": product,
                "cadence": "daily",
                "metrics_json": {
                    "event_total": total,
                    "event_types": len(evts_sorted),
                    "top_events": top,
                    "source": "ga4",
                },
                "updated_at": now,
            }
        )

    # --- customer: active users (DAU) + 7d unique approx from daily users sum isn't unique —
    # use latest day users as DAU; WAU = sum of daily users over last 7 (upper bound / engagement)
    customer_out = []
    for product, days in by_product_days.items():
        days_sorted = sorted(days, key=lambda x: x["period_date"])
        for i, d in enumerate(days_sorted):
            window = days_sorted[max(0, i - 6) : i + 1]
            wau_proxy = sum(x["users"] for x in window)
            customer_out.append(
                {
                    "period_date": d["period_date"].isoformat(),
                    "product": product,
                    "cadence": "daily",
                    "metrics_json": {
                        "dau": d["users"],
                        "sessions": d["sessions"],
                        "wau_engagement_sum": wau_proxy,
                        "active_days_7d": len(window),
                        "source": "ga4",
                    },
                    "updated_at": now,
                }
            )

    out = {
        "growth": _upsert_mart(client, cfg, "growth", growth_out),
        "product": _upsert_mart(client, cfg, "product", product_out),
        "customer": _upsert_mart(client, cfg, "customer", customer_out),
    }
    return out


def _upsert_mart(
    client: Any,
    cfg: BigQueryConfig,
    mart_name: str,
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    if not rows:
        return {"status": "empty", "rows_upserted": 0}
    from google.cloud import bigquery

    mart_id = f"{cfg.project}.marts.{mart_name}"
    staging = f"{mart_id}_ga4_staging"
    dest = client.get_table(mart_id)
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
        MERGE `{mart_id}` T
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
    return {"status": "ok", "rows_upserted": len(rows)}
