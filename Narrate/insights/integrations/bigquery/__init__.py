"""BigQuery integrations for Insights Digests."""

from insights.integrations.bigquery.config import BigQueryConfig

# Loaders imported lazily by callers; config is always safe.
__all__ = [
    "BigQueryConfig",
    "BigQuerySnapshotLoader",
    "BigQueryStrategyLoader",
    "get_bigquery_client",
]


def __getattr__(name: str):
    if name == "get_bigquery_client":
        from insights.integrations.bigquery.client import get_bigquery_client

        return get_bigquery_client
    if name == "BigQuerySnapshotLoader":
        from insights.integrations.bigquery.snapshot_loader import BigQuerySnapshotLoader

        return BigQuerySnapshotLoader
    if name == "BigQueryStrategyLoader":
        from insights.integrations.bigquery.strategy_loader import BigQueryStrategyLoader

        return BigQueryStrategyLoader
    raise AttributeError(name)
