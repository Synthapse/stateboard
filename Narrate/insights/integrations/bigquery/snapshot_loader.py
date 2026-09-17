"""Load InsightsSnapshot rows from marts_insights.snapshot_daily."""

from __future__ import annotations

from insights.domain.models import InsightsSnapshot, Product
from insights.integrations.bigquery.client import get_bigquery_client
from insights.integrations.bigquery.config import BigQueryConfig


class BigQuerySnapshotLoader:
    """Integration: read vital-few metrics for Digests enrichment details."""

    def __init__(self, config: BigQueryConfig | None = None) -> None:
        self.config = config or BigQueryConfig.from_env()

    def load_latest(self, product: Product) -> InsightsSnapshot:
        from google.cloud import bigquery

        client = get_bigquery_client(self.config.project)
        sql = f"""
            SELECT
              period_date,
              product,
              schema_version,
              period_start,
              period_end,
              sessions,
              sessions_delta_pct,
              users,
              cloud_cost_usd,
              cloud_cost_delta_pct,
              ai_cost_usd,
              reliability_flags,
              watch_bullets
            FROM `{self.config.snapshot_table}`
            WHERE product = @product
            ORDER BY period_date DESC
            LIMIT 1
        """
        job = client.query(
            sql,
            job_config=bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("product", "STRING", product.value),
                ]
            ),
            location=self.config.location,
        )
        rows = list(job.result())
        if not rows:
            raise LookupError(
                f"No snapshot for product={product.value} in {self.config.snapshot_table}"
            )
        return InsightsSnapshot.model_validate(dict(rows[0].items()))
