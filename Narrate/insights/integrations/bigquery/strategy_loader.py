"""Load / save ProductStrategyHold in marts_insights.product_strategy."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from insights.domain.models import Cadence, Product, ProductStrategyHold
from insights.integrations.bigquery.client import get_bigquery_client, query_job_config
from insights.integrations.bigquery.config import BigQueryConfig


class BigQueryStrategyLoader:
    """Integration: living GTM hold per product × cadence."""

    def __init__(self, config: BigQueryConfig | None = None) -> None:
        self.config = config or BigQueryConfig.from_env()

    def load_latest(self, product: Product, cadence: Cadence) -> ProductStrategyHold:
        from google.cloud import bigquery

        client = get_bigquery_client(self.config.project)
        sql = f"""
            SELECT payload_json
            FROM `{self.config.strategy_table}`
            WHERE product = @product AND cadence = @cadence
            ORDER BY updated_at DESC
            LIMIT 1
        """
        job = client.query(
            sql,
            job_config=query_job_config(
                query_parameters=[
                    bigquery.ScalarQueryParameter("product", "STRING", product.value),
                    bigquery.ScalarQueryParameter("cadence", "STRING", cadence.value),
                ]
            ),
            location=self.config.location,
        )
        rows = list(job.result())
        if not rows:
            raise LookupError(
                f"No strategy for {product.value}/{cadence.value} in {self.config.strategy_table}"
            )
        payload = rows[0]["payload_json"]
        if isinstance(payload, str):
            payload = json.loads(payload)
        return ProductStrategyHold.model_validate(payload)

    def save(self, hold: ProductStrategyHold) -> None:
        """Upsert via load + MERGE (JSON as string; avoid streaming insert quirks)."""
        from google.cloud import bigquery

        client = get_bigquery_client(self.config.project)
        table_id = self.config.strategy_table
        updated = hold.updated_at or datetime.now(timezone.utc)
        row = {
            "product": hold.product.value,
            "cadence": hold.cadence.value,
            "schema_version": hold.schema_version,
            "period_date": hold.period_date.isoformat(),
            "title": hold.title,
            "product_description": hold.product_description,
            "target_market": hold.target_market,
            "budget_range": hold.budget_range,
            "timeline_constraints": hold.timeline_constraints,
            "executive_summary": hold.executive_summary,
            "payload_json": hold.model_dump_json(),
            "refreshed_by": hold.refreshed_by,
            "updated_at": updated.isoformat(),
        }
        staging_id = f"{table_id}_staging"
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
        ON T.product = S.product AND T.cadence = S.cadence AND T.period_date = S.period_date
        WHEN MATCHED THEN UPDATE SET
          schema_version = S.schema_version,
          title = S.title,
          product_description = S.product_description,
          target_market = S.target_market,
          budget_range = S.budget_range,
          timeline_constraints = S.timeline_constraints,
          executive_summary = S.executive_summary,
          payload_json = S.payload_json,
          refreshed_by = S.refreshed_by,
          updated_at = S.updated_at
        WHEN NOT MATCHED THEN INSERT ROW
        """
        client.query(merge_sql, location=self.config.location).result()
