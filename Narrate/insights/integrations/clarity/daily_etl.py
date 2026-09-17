"""Daily Clarity Data Export API → BigQuery `raw_clarity.daily_insights`."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any

from insights.domain.models import Product
from insights.integrations.clarity.loader import ClarityLoader, clarity_project_id, clarity_token

TABLE_ID_SUFFIX = "raw_clarity.daily_insights"


@dataclass(frozen=True)
class ClarityDayRow:
    product: str
    period_date: date
    clarity_project_id: str
    num_of_days: int
    payload_json: Any
    status: str
    ingested_at: datetime

    def to_json(self) -> dict[str, Any]:
        return {
            "product": self.product,
            "period_date": self.period_date.isoformat(),
            "clarity_project_id": self.clarity_project_id,
            "num_of_days": self.num_of_days,
            "payload_json": self.payload_json,
            "status": self.status,
            "ingested_at": self.ingested_at.isoformat(),
        }


def _schema():
    from google.cloud import bigquery

    return [
        bigquery.SchemaField("product", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("period_date", "DATE", mode="REQUIRED"),
        bigquery.SchemaField("clarity_project_id", "STRING"),
        bigquery.SchemaField("num_of_days", "INT64"),
        bigquery.SchemaField("payload_json", "JSON"),
        bigquery.SchemaField("status", "STRING"),
        bigquery.SchemaField("ingested_at", "TIMESTAMP", mode="REQUIRED"),
    ]


class ClarityDailyEtl:
    """
    One API call per product (numOfDays=1..3) → upsert raw_clarity.daily_insights.
    Clarity caps history at 3 days and ~10 requests/project/day — keep to 1 call/product/day.
    """

    def __init__(self, loader: ClarityLoader | None = None) -> None:
        self.loader = loader or ClarityLoader()

    def run(
        self,
        product: Product | str | None = None,
        *,
        num_of_days: int = 3,
        as_of: date | None = None,
    ) -> list[dict[str, Any]]:
        as_of = as_of or date.today()
        days = max(1, min(int(num_of_days), 3))
        products = [Product(product)] if product else list(Product)

        from insights.integrations.bigquery.client import get_bigquery_client
        from insights.integrations.bigquery.config import BigQueryConfig

        cfg = BigQueryConfig.from_env()
        client = get_bigquery_client(cfg.project)
        table_id = f"{cfg.project}.{TABLE_ID_SUFFIX}"
        self._ensure_table(client, table_id)

        results: list[dict[str, Any]] = []
        rows: list[ClarityDayRow] = []

        for prod in products:
            cid = clarity_project_id(prod)
            token = clarity_token(prod)
            if not cid:
                results.append({"product": prod.value, "status": "skipped_no_project"})
                continue
            if not token:
                results.append({"product": prod.value, "status": "skipped_no_keys"})
                continue
            try:
                payload = self.loader.fetch(token, num_of_days=days, project_id=cid)
                row = ClarityDayRow(
                    product=prod.value,
                    period_date=as_of,
                    clarity_project_id=cid,
                    num_of_days=days,
                    payload_json=payload,
                    status="ok",
                    ingested_at=datetime.now(timezone.utc),
                )
                rows.append(row)
                results.append(
                    {
                        "product": prod.value,
                        "period_date": as_of.isoformat(),
                        "clarity_project_id": cid,
                        "num_of_days": days,
                        "status": "fetched",
                    }
                )
            except Exception as exc:
                print(f"Clarity ETL {prod.value}: {exc}")
                results.append(
                    {
                        "product": prod.value,
                        "status": "error",
                        "error": str(exc)[:200],
                    }
                )

        if rows:
            self._merge_rows(client, table_id, rows)
            for r in results:
                if r.get("status") == "fetched":
                    r["status"] = "ok"
        return results

    def _merge_rows(self, client: Any, table_id: str, rows: list[ClarityDayRow]) -> None:
        from google.cloud import bigquery

        staging_id = f"{table_id}_staging"
        payload = []
        for r in rows:
            j = r.to_json()
            # BQ load JSON type wants a JSON-encoded string in NDJSON loads sometimes;
            # pass object — client serializes; if fails, stringify.
            if j["payload_json"] is not None and not isinstance(j["payload_json"], str):
                j["payload_json"] = json.dumps(j["payload_json"])
            payload.append(j)

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
          clarity_project_id = S.clarity_project_id,
          num_of_days = S.num_of_days,
          payload_json = S.payload_json,
          status = S.status,
          ingested_at = S.ingested_at
        WHEN NOT MATCHED THEN INSERT (
          product, period_date, clarity_project_id, num_of_days,
          payload_json, status, ingested_at
        ) VALUES (
          S.product, S.period_date, S.clarity_project_id, S.num_of_days,
          S.payload_json, S.status, S.ingested_at
        )
        """
        try:
            client.query(merge_sql).result()
        except Exception as exc:
            if "streaming buffer" not in str(exc).lower():
                raise
            print("raw_clarity.daily_insights: recreating table after streaming buffer")
            self._recreate_empty(client, table_id)
            client.query(f"INSERT INTO `{table_id}` SELECT * FROM `{staging_id}`").result()

    def _recreate_empty(self, client: Any, table_id: str) -> None:
        client.query(
            f"""
            CREATE OR REPLACE TABLE `{table_id}` (
              product STRING NOT NULL,
              period_date DATE NOT NULL,
              clarity_project_id STRING,
              num_of_days INT64,
              payload_json JSON,
              status STRING,
              ingested_at TIMESTAMP NOT NULL
            )
            PARTITION BY period_date
            CLUSTER BY product
            """
        ).result()

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
