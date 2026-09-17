"""Daily Langfuse API → BigQuery `raw_langfuse.daily_metrics` (one row per product × day)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any

from insights.domain.models import Product
from insights.integrations.langfuse.metrics_loader import LangfuseMetricsLoader, _keys_for
from insights.integrations.products import get_sources

TABLE_ID_SUFFIX = "raw_langfuse.daily_metrics"


@dataclass(frozen=True)
class LangfuseDayRow:
    product: str
    period_date: date
    langfuse_project_id: str | None
    langfuse_project_name: str | None
    total_cost_usd: float | None
    trace_count: int | None
    source: str
    ingested_at: datetime

    def to_json(self) -> dict[str, Any]:
        return {
            "product": self.product,
            "period_date": self.period_date.isoformat(),
            "langfuse_project_id": self.langfuse_project_id,
            "langfuse_project_name": self.langfuse_project_name,
            "total_cost_usd": self.total_cost_usd,
            "trace_count": self.trace_count,
            "source": self.source,
            "ingested_at": self.ingested_at.isoformat(),
        }


def _schema():
    from google.cloud import bigquery

    return [
        bigquery.SchemaField("product", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("period_date", "DATE", mode="REQUIRED"),
        bigquery.SchemaField("langfuse_project_id", "STRING"),
        bigquery.SchemaField("langfuse_project_name", "STRING"),
        bigquery.SchemaField("total_cost_usd", "FLOAT"),
        bigquery.SchemaField("trace_count", "INT64"),
        bigquery.SchemaField("source", "STRING"),
        bigquery.SchemaField("ingested_at", "TIMESTAMP", mode="REQUIRED"),
    ]


class LangfuseDailyEtl:
    """
    Pull per-day cost + observation counts from Langfuse and upsert into cognispace.
    Uses load job + MERGE (not streaming insert) so DML works immediately.
    """

    def __init__(self, loader: LangfuseMetricsLoader | None = None) -> None:
        self.loader = loader or LangfuseMetricsLoader()

    def run(
        self,
        product: Product | str | None = None,
        *,
        lookback_days: int = 1,
        as_of: date | None = None,
    ) -> list[dict[str, Any]]:
        """
        Upsert daily metrics for yesterday (default) or the last `lookback_days` days.
        `as_of` defaults to today; the newest day written is as_of - 1 (complete UTC day).
        """
        as_of = as_of or date.today()
        end = as_of - timedelta(days=1)
        start = end - timedelta(days=max(lookback_days, 1) - 1)
        products = [Product(product)] if product else list(Product)

        from insights.integrations.bigquery.client import get_bigquery_client
        from insights.integrations.bigquery.config import BigQueryConfig

        cfg = BigQueryConfig.from_env()
        client = get_bigquery_client(cfg.project)
        table_id = f"{cfg.project}.{TABLE_ID_SUFFIX}"
        self._ensure_table(client, table_id)

        results: list[dict[str, Any]] = []
        rows: list[LangfuseDayRow] = []

        for prod in products:
            pub, sec = _keys_for(prod)
            if not pub or not sec:
                results.append({"product": prod.value, "status": "skipped_no_keys"})
                continue
            sources = get_sources(prod)
            day = start
            while day <= end:
                try:
                    row = self._fetch_day(prod, sources, pub, sec, day)
                    rows.append(row)
                    results.append(
                        {
                            "product": prod.value,
                            "period_date": day.isoformat(),
                            "total_cost_usd": row.total_cost_usd,
                            "trace_count": row.trace_count,
                            "status": "fetched",
                        }
                    )
                except Exception as exc:
                    print(f"Langfuse ETL {prod.value} {day}: {exc}")
                    results.append(
                        {
                            "product": prod.value,
                            "period_date": day.isoformat(),
                            "status": "error",
                            "error": str(exc)[:200],
                        }
                    )
                day += timedelta(days=1)

        if rows:
            self._merge_rows(client, table_id, rows)
            for r in results:
                if r.get("status") == "fetched":
                    r["status"] = "ok"
            # Promote into BI mart (empty shells → usable marts.ai)
            try:
                from insights.integrations.langfuse.marts_ai import promote_marts_ai

                mart = promote_marts_ai(
                    product=Product(product).value if product else None,
                    lookback_days=max(lookback_days, 1),
                )
                results.append({"status": "marts_ai", **mart})
            except Exception as exc:
                print(f"marts.ai promote failed: {exc}")
                results.append({"status": "marts_ai_error", "error": str(exc)[:200]})
        return results

    def _fetch_day(
        self,
        product: Product,
        sources: Any,
        pub: str,
        sec: str,
        day: date,
    ) -> LangfuseDayRow:
        metrics = self.loader.fetch_range(pub, sec, day, day)
        return LangfuseDayRow(
            product=product.value,
            period_date=day,
            langfuse_project_id=sources.langfuse_project_id,
            langfuse_project_name=sources.langfuse_project_name,
            total_cost_usd=metrics.total_cost_usd,
            trace_count=metrics.trace_count,
            source=metrics.source,
            ingested_at=datetime.now(timezone.utc),
        )

    def _merge_rows(self, client: Any, table_id: str, rows: list[LangfuseDayRow]) -> None:
        """Load NDJSON → staging (batch load), MERGE into target. Avoids streaming buffer."""
        from google.cloud import bigquery

        staging_id = f"{table_id}_staging"
        payload = [r.to_json() for r in rows]
        load_config = bigquery.LoadJobConfig(
            schema=_schema(),
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
            source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        )
        client.load_table_from_json(payload, staging_id, job_config=load_config).result()

        merge_sql = f"""
        MERGE `{table_id}` T
        USING `{staging_id}` S
        ON T.product = S.product AND T.period_date = S.period_date
        WHEN MATCHED THEN UPDATE SET
          langfuse_project_id = S.langfuse_project_id,
          langfuse_project_name = S.langfuse_project_name,
          total_cost_usd = S.total_cost_usd,
          trace_count = S.trace_count,
          source = S.source,
          ingested_at = S.ingested_at
        WHEN NOT MATCHED THEN INSERT (
          product, period_date, langfuse_project_id, langfuse_project_name,
          total_cost_usd, trace_count, source, ingested_at
        ) VALUES (
          S.product, S.period_date, S.langfuse_project_id, S.langfuse_project_name,
          S.total_cost_usd, S.trace_count, S.source, S.ingested_at
        )
        """
        try:
            client.query(merge_sql).result()
        except Exception as exc:
            msg = str(exc)
            if "streaming buffer" not in msg.lower():
                raise
            # Prior streaming inserts left a buffer — recreate empty target, then insert.
            print("raw_langfuse.daily_metrics: clearing streaming-buffer table, then reload")
            self._recreate_empty(client, table_id)
            client.query(
                f"""
                INSERT INTO `{table_id}`
                SELECT * FROM `{staging_id}`
                """
            ).result()

    def _recreate_empty(self, client: Any, table_id: str) -> None:
        from google.cloud import bigquery

        # CREATE OR REPLACE bypasses streaming-buffer DELETE limits
        client.query(
            f"""
            CREATE OR REPLACE TABLE `{table_id}` (
              product STRING NOT NULL,
              period_date DATE NOT NULL,
              langfuse_project_id STRING,
              langfuse_project_name STRING,
              total_cost_usd FLOAT64,
              trace_count INT64,
              source STRING,
              ingested_at TIMESTAMP NOT NULL
            )
            PARTITION BY period_date
            CLUSTER BY product
            """
        ).result()
        # refresh metadata cache
        client.get_table(table_id)

    @staticmethod
    def _ensure_table(client: Any, table_id: str) -> None:
        from google.cloud import bigquery

        try:
            client.get_table(table_id)
            return
        except Exception:
            pass
        table = bigquery.Table(table_id, schema=_schema())
        table.time_partitioning = bigquery.TimePartitioning(
            type_=bigquery.TimePartitioningType.DAY,
            field="period_date",
        )
        table.clustering_fields = ["product"]
        client.create_table(table, exists_ok=True)
