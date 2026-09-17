"""SnapshotRepository adapter → BigQuerySnapshotLoader integration."""

from __future__ import annotations

from insights.domain.models import Cadence, InsightsSnapshot, Product
from insights.infrastructure.fixture_snapshot_repo import FixtureSnapshotRepository
from insights.integrations.bigquery.config import BigQueryConfig
from insights.integrations.bigquery.snapshot_loader import BigQuerySnapshotLoader


class BigQuerySnapshotRepository:
    def __init__(self, config: BigQueryConfig | None = None) -> None:
        self._loader = BigQuerySnapshotLoader(config)
        self._fallback = FixtureSnapshotRepository()

    def get_latest(self, product: Product, cadence: Cadence) -> InsightsSnapshot:
        try:
            return self._loader.load_latest(product)
        except Exception as exc:
            print(f"BQ snapshot load failed ({exc}); using fixture")
            return self._fallback.get_latest(product, cadence)
