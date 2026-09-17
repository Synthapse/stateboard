"""Build InsightsSnapshot rows from GA4 + Billing → marts_insights.snapshot_daily."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from insights.domain.models import InsightsSnapshot, Product
from insights.integrations.bigquery.client import get_bigquery_client
from insights.integrations.bigquery.config import BigQueryConfig
from insights.integrations.products import (
    BQ_HUB_PROJECT,
    PRODUCT_SOURCES,
    ProductSources,
    billing_export_table_id,
    get_sources,
)

_SQL_DIR = Path(__file__).parent / "sql"


def _load_sql(name: str, **repl: str | int) -> str:
    text = (_SQL_DIR / name).read_text()
    for key, val in repl.items():
        text = text.replace("{{" + key + "}}", str(val))
    return text


def _pct_delta(current: float | None, prior: float | None) -> float | None:
    if current is None or prior is None or prior == 0:
        return None
    return round((current - prior) / prior * 100.0, 2)


def _prefer_ai_cost(*candidates: float | None) -> float | None:
    """First positive cost wins; else first non-None (incl. 0)."""
    first_non_null: float | None = None
    for c in candidates:
        if c is None:
            continue
        if first_non_null is None:
            first_non_null = float(c)
        if float(c) > 0:
            return float(c)
    return first_non_null


class BigQuerySnapshotBuilder:
    """
    Load path: GA4 + Billing + Langfuse + Clarity
    → InsightsSnapshot → snapshot_daily.
    See docs/ui-setup-load-paths.md for Console / API key setup.
    """

    def __init__(
        self,
        config: BigQueryConfig | None = None,
        *,
        lookback_days: int = 7,
    ) -> None:
        self.config = config or BigQueryConfig.from_env()
        self.lookback_days = lookback_days

    def build_one(self, product: Product | str) -> InsightsSnapshot:
        sources = get_sources(product)
        period_end = date.today() - timedelta(days=1)
        period_start = period_end - timedelta(days=self.lookback_days - 1)

        sessions, users = self._ga4_growth(sources)
        sessions_prior = self._ga4_sessions_prior(sources)
        # Prefer warehouse growth when GA4 live window is empty
        if sessions is None and users is None:
            sessions, users, sessions_prior = self._growth_from_marts(sources.product.value)

        cloud_cost, billing_ai = self._billing_cost(sources)
        cloud_prior = self._billing_cost_prior(sources)
        if cloud_cost is None:
            cloud_cost, cloud_prior = self._cloud_from_marts(sources.product.value)

        from insights.integrations.clarity.loader import ClarityLoader
        from insights.integrations.langfuse.metrics_loader import LangfuseMetricsLoader

        lf = LangfuseMetricsLoader().load(sources.product, lookback_days=self.lookback_days)
        clarity = ClarityLoader().load(sources.product)

        warehouse_ai = self._ai_from_warehouse(sources.product.value)
        # Prefer positive Langfuse $; 0 with traces often means pricing unset in Langfuse
        ai_cost = _prefer_ai_cost(lf.total_cost_usd, warehouse_ai, billing_ai)

        flags: list[str] = []
        if sessions is None and users is None:
            flags.append(f"ga4:no_events:{sources.ga4_dataset}")
        if lf.trace_count is not None:
            flags.append(f"langfuse:traces={lf.trace_count}")
        if clarity.project_id and clarity.status != "none":
            flags.append(f"clarity:{clarity.status}:{clarity.project_id}")

        rel = self._reliability_flags(sources.product.value)
        watch: list[str] = list(rel["watch"])
        reliability_flags = self._merge_reliability_flags(flags, rel["flags"])
        if sessions is None and users is None:
            watch.append(f"GA4 events_* not ready in {sources.ga4_dataset} — wait for daily export")
        if clarity.note and clarity.status in ("no_token", "error"):
            watch.append(clarity.note)
        if (lf.trace_count or 0) > 0 and (lf.total_cost_usd or 0) == 0 and (ai_cost or 0) == 0:
            watch.append(
                "Langfuse has traces but $0 cost — enable model pricing in Langfuse project settings"
            )
        elif ai_cost is None and (lf.total_cost_usd is None) and billing_ai is None:
            watch.append("AI $ unavailable — set Langfuse API keys or wait for Billing Gemini SKUs")
        if cloud_cost is None:
            watch.append(f"Billing empty for project {sources.gcp_project_id}")

        # Digest-friendly: no null metrics when a source was queried
        sessions_out = 0 if sessions is None else sessions
        users_out = 0 if users is None else users
        cloud_out = 0.0 if cloud_cost is None else cloud_cost
        ai_out = 0.0 if ai_cost is None else ai_cost
        sessions_delta = _pct_delta(
            float(sessions) if sessions is not None else None,
            float(sessions_prior) if sessions_prior is not None else None,
        )
        cloud_delta = _pct_delta(cloud_cost, cloud_prior)

        snap = InsightsSnapshot(
            schema_version=1,
            product=sources.product,
            period_date=period_end,
            period_start=datetime.combine(period_start, datetime.min.time(), tzinfo=timezone.utc),
            period_end=datetime.combine(period_end, datetime.max.time(), tzinfo=timezone.utc),
            sessions=sessions_out,
            sessions_delta_pct=0.0 if sessions_delta is None else sessions_delta,
            users=users_out,
            cloud_cost_usd=cloud_out,
            cloud_cost_delta_pct=0.0 if cloud_delta is None else cloud_delta,
            ai_cost_usd=ai_out,
            reliability_flags=reliability_flags,
            watch_bullets=watch[:3],
        )
        self._insert_snapshot(snap)
        return snap

    @staticmethod
    def _merge_reliability_flags(other: list[str], health: list[str], *, max_flags: int = 3) -> list[str]:
        """Prefer health/exception flags so Digests always show reliability when known."""
        out: list[str] = []
        for f in health:
            if f and f not in out:
                out.append(f)
        for f in other:
            if len(out) >= max_flags:
                break
            if f and f not in out:
                out.append(f)
        return out[:max_flags]

    def build_all(self) -> list[InsightsSnapshot]:
        return [self.build_one(p) for p in Product]

    def _ga4_growth(self, sources: ProductSources) -> tuple[int | None, int | None]:
        sql = _load_sql(
            "ga4_growth.sql",
            ga4_events=f"{BQ_HUB_PROJECT}.{sources.ga4_dataset}.events_*",
            lookback_days=self.lookback_days,
        )
        row = self._query_one(sql, location=self._ga4_location(sources))
        if not row:
            print(f"GA4 growth empty/missing for {sources.product.value} ({sources.ga4_dataset})")
            return None, None
        return _as_int(row.get("sessions")), _as_int(row.get("users"))

    def _ga4_sessions_prior(self, sources: ProductSources) -> int | None:
        sql = _load_sql(
            "ga4_growth_prior.sql",
            ga4_events=f"{BQ_HUB_PROJECT}.{sources.ga4_dataset}.events_*",
            lookback_days=self.lookback_days,
        )
        row = self._query_one(sql, location=self._ga4_location(sources))
        return _as_int(row.get("sessions_prior")) if row else None

    @staticmethod
    def _ga4_location(sources: ProductSources) -> str:
        # Prefer per-product registry (KIH=EU, Lindle/YCA=europe-central2).
        # Overrides: BQ_GA4_LOCATION_<PRODUCT>, then BQ_GA4_LOCATION as last resort.
        import os

        per = os.getenv(f"BQ_GA4_LOCATION_{sources.product.value.upper()}", "").strip()
        if per:
            return per
        if sources.ga4_location:
            return sources.ga4_location
        return os.getenv("BQ_GA4_LOCATION", "europe-central2").strip()

    def _billing_cost(self, sources: ProductSources) -> tuple[float | None, float | None]:
        table = (
            f"{BQ_HUB_PROJECT}.raw_billing."
            f"{billing_export_table_id(sources.billing_account_id)}"
        )
        sql = _load_sql(
            "billing_cost.sql",
            billing_table=table,
            lookback_days=self.lookback_days,
        )
        row = self._query_one(sql, gcp_project=sources.gcp_project_id)
        cloud = _as_float(row.get("cloud_cost_usd")) if row else None
        ai = _as_float(row.get("ai_cost_usd")) if row else None
        if cloud is None:
            # Export may lag or have gaps; use latest available window for this project.
            fallback = _load_sql(
                "billing_cost_latest.sql",
                billing_table=table,
                lookback_days=self.lookback_days,
            )
            row = self._query_one(fallback, gcp_project=sources.gcp_project_id)
            cloud = _as_float(row.get("cloud_cost_usd")) if row else None
            if ai is None:
                ai = _as_float(row.get("ai_cost_usd")) if row else None
            if cloud is not None:
                print(
                    f"Billing lookback empty for {sources.product.value} — "
                    f"using latest available window (${cloud:.4f})"
                )
        if cloud is None:
            print(f"Billing empty/missing for {sources.product.value} ({table})")
        return cloud, ai

    def _billing_cost_prior(self, sources: ProductSources) -> float | None:
        table = (
            f"{BQ_HUB_PROJECT}.raw_billing."
            f"{billing_export_table_id(sources.billing_account_id)}"
        )
        sql = _load_sql(
            "billing_cost_prior.sql",
            billing_table=table,
            lookback_days=self.lookback_days,
        )
        row = self._query_one(sql, gcp_project=sources.gcp_project_id)
        return _as_float(row.get("cloud_cost_prior")) if row else None

    def _ai_from_warehouse(self, product: str) -> float | None:
        """Sum raw_langfuse.daily_metrics over lookback (skip null days)."""
        sql = f"""
        SELECT CAST(SUM(total_cost_usd) AS FLOAT64) AS ai_cost_usd
        FROM `{self.config.project}.raw_langfuse.daily_metrics`
        WHERE product = @product
          AND period_date BETWEEN
            DATE_SUB(CURRENT_DATE(), INTERVAL @lookback DAY)
            AND DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
        """
        from google.cloud import bigquery

        from insights.integrations.bigquery.client import get_bigquery_client, query_job_config

        try:
            client = get_bigquery_client(self.config.project)
            rows = list(
                client.query(
                    sql,
                    job_config=query_job_config(
                        query_parameters=[
                            bigquery.ScalarQueryParameter("product", "STRING", product),
                            bigquery.ScalarQueryParameter(
                                "lookback", "INT64", int(self.lookback_days)
                            ),
                        ]
                    ),
                    location=self.config.location,
                ).result()
            )
        except Exception:
            return None
        if not rows:
            return None
        return _as_float(rows[0].get("ai_cost_usd"))

    def _growth_from_marts(
        self, product: str
    ) -> tuple[int | None, int | None, int | None]:
        """Fallback sessions/users (+ prior) from marts.growth."""
        sql = f"""
        SELECT
          SAFE_CAST(JSON_VALUE(metrics_json, '$.sessions') AS INT64) AS sessions,
          SAFE_CAST(JSON_VALUE(metrics_json, '$.users') AS INT64) AS users,
          period_date
        FROM `{self.config.project}.marts.growth`
        WHERE product = @product
        ORDER BY period_date DESC
        LIMIT 2
        """
        from google.cloud import bigquery

        from insights.integrations.bigquery.client import get_bigquery_client, query_job_config

        try:
            client = get_bigquery_client(self.config.project)
            rows = list(
                client.query(
                    sql,
                    job_config=query_job_config(
                        query_parameters=[
                            bigquery.ScalarQueryParameter("product", "STRING", product)
                        ]
                    ),
                    location=self.config.location,
                ).result()
            )
        except Exception:
            return None, None, None
        if not rows:
            return None, None, None
        sessions = _as_int(rows[0].get("sessions"))
        users = _as_int(rows[0].get("users"))
        prior = _as_int(rows[1].get("sessions")) if len(rows) > 1 else None
        return sessions, users, prior

    def _cloud_from_marts(self, product: str) -> tuple[float | None, float | None]:
        """Sum marts.cost over lookback; prior = previous equal window if present."""
        sql = f"""
        SELECT
          period_date,
          SAFE_CAST(JSON_VALUE(metrics_json, '$.cloud_cost_usd') AS FLOAT64) AS cloud_cost_usd
        FROM `{self.config.project}.marts.cost`
        WHERE product = @product
          AND period_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 120 DAY)
        ORDER BY period_date DESC
        """
        from google.cloud import bigquery

        from insights.integrations.bigquery.client import get_bigquery_client, query_job_config

        try:
            client = get_bigquery_client(self.config.project)
            rows = list(
                client.query(
                    sql,
                    job_config=query_job_config(
                        query_parameters=[
                            bigquery.ScalarQueryParameter("product", "STRING", product)
                        ]
                    ),
                    location=self.config.location,
                ).result()
            )
        except Exception:
            return None, None
        if not rows:
            return None, None
        # Latest lookback_days of available cost days
        window = rows[: self.lookback_days]
        cloud = sum(float(r["cloud_cost_usd"] or 0) for r in window)
        prior_rows = rows[self.lookback_days : self.lookback_days * 2]
        prior = sum(float(r["cloud_cost_usd"] or 0) for r in prior_rows) if prior_rows else None
        return cloud, prior

    def _reliability_flags(self, product: str) -> dict[str, list[str]]:
        """Read latest marts.reliability for health + exception digest flags."""
        sql = f"""
        SELECT metrics_json
        FROM `{self.config.project}.marts.reliability`
        WHERE product = @product
        ORDER BY period_date DESC
        LIMIT 1
        """
        from google.cloud import bigquery

        from insights.integrations.bigquery.client import get_bigquery_client, query_job_config

        flags: list[str] = []
        watch: list[str] = []
        try:
            client = get_bigquery_client(self.config.project)
            rows = list(
                client.query(
                    sql,
                    job_config=query_job_config(
                        query_parameters=[
                            bigquery.ScalarQueryParameter("product", "STRING", product)
                        ]
                    ),
                    location=self.config.location,
                ).result()
            )
        except Exception:
            return {"flags": flags, "watch": watch}
        if not rows:
            return {"flags": flags, "watch": watch}
        metrics = rows[0].get("metrics_json") or {}
        if isinstance(metrics, str):
            try:
                metrics = json.loads(metrics)
            except Exception:
                metrics = {}
        down = int(metrics.get("services_down") or 0)
        total = int(metrics.get("services_total") or 0)
        failing = metrics.get("failing") or []
        exc_n = int(metrics.get("exception_count") or 0)
        if total:
            flags.append(f"health:{total - down}/{total}up")
        if failing:
            watch.append("health fail: " + ",".join(str(x) for x in failing[:3]))
        if exc_n:
            flags.append(f"exceptions:{exc_n}")
            types = metrics.get("exception_types") or []
            if types:
                watch.append("exceptions: " + ",".join(str(t) for t in types[:3]))
        return {"flags": flags, "watch": watch}

    def _query_one(
        self,
        sql: str,
        gcp_project: str | None = None,
        *,
        location: str | None = None,
    ) -> dict[str, Any] | None:
        from google.cloud import bigquery

        from insights.integrations.bigquery.client import get_bigquery_client, query_job_config

        client = get_bigquery_client(self.config.project)
        params = []
        if gcp_project is not None:
            params.append(bigquery.ScalarQueryParameter("gcp_project", "STRING", gcp_project))
        try:
            job = client.query(
                sql,
                job_config=query_job_config(query_parameters=params),
                location=location or self.config.location,
            )
            rows = list(job.result())
        except Exception as exc:
            msg = str(exc)
            if "Not found" in msg or "notFound" in msg:
                print(f"BQ table missing (skip): {exc.__class__.__name__}")
            else:
                print(f"BQ query failed: {exc}")
            return None
        if not rows:
            return None
        return dict(rows[0].items())

    def _insert_snapshot(self, snap: InsightsSnapshot) -> None:
        """Upsert via load + MERGE (avoid streaming-buffer DELETE issues)."""
        from google.cloud import bigquery

        client = get_bigquery_client(self.config.project)
        table_id = self.config.snapshot_table
        row = {
            "period_date": snap.period_date.isoformat(),
            "product": snap.product.value,
            "schema_version": snap.schema_version,
            "period_start": snap.period_start.isoformat() if snap.period_start else None,
            "period_end": snap.period_end.isoformat() if snap.period_end else None,
            "sessions": snap.sessions,
            "sessions_delta_pct": snap.sessions_delta_pct,
            "users": snap.users,
            "cloud_cost_usd": snap.cloud_cost_usd,
            "cloud_cost_delta_pct": snap.cloud_cost_delta_pct,
            "ai_cost_usd": snap.ai_cost_usd,
            "reliability_flags": snap.reliability_flags,
            "watch_bullets": snap.watch_bullets,
            "payload_json": json.dumps(json.loads(snap.model_dump_json())),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        staging_id = f"{table_id}_staging"
        # Infer schema from destination
        dest = client.get_table(table_id)
        load_config = bigquery.LoadJobConfig(
            schema=dest.schema,
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
            source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        )
        client.load_table_from_json([row], staging_id, job_config=load_config).result()
        merge_sql = f"""
        MERGE `{table_id}` T
        USING `{staging_id}` S
        ON T.product = S.product AND T.period_date = S.period_date
        WHEN MATCHED THEN UPDATE SET
          schema_version = S.schema_version,
          period_start = S.period_start,
          period_end = S.period_end,
          sessions = S.sessions,
          sessions_delta_pct = S.sessions_delta_pct,
          users = S.users,
          cloud_cost_usd = S.cloud_cost_usd,
          cloud_cost_delta_pct = S.cloud_cost_delta_pct,
          ai_cost_usd = S.ai_cost_usd,
          reliability_flags = S.reliability_flags,
          watch_bullets = S.watch_bullets,
          payload_json = S.payload_json,
          updated_at = S.updated_at
        WHEN NOT MATCHED THEN INSERT ROW
        """
        try:
            client.query(merge_sql, location=self.config.location).result()
        except Exception as exc:
            if "streaming buffer" not in str(exc).lower():
                raise
            print("snapshot_daily: MERGE blocked by streaming buffer — INSERT only")
            client.query(
                f"INSERT INTO `{table_id}` SELECT * FROM `{staging_id}`",
                location=self.config.location,
            ).result()


def _as_int(v: Any) -> int | None:
    if v is None:
        return None
    return int(v)


def _as_float(v: Any) -> float | None:
    if v is None:
        return None
    return float(v)
