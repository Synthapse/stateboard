"""Application service: load Snapshot + strategy for one Digest run."""

from __future__ import annotations

from dataclasses import dataclass

from insights.domain.models import Cadence, InsightsSnapshot, Product, ProductStrategyHold
from insights.domain.ports import SnapshotRepository, StrategyRepository


@dataclass(frozen=True)
class DigestContext:
    """Loaded inputs for DigestRunUseCase (BQ or fixture via repos)."""

    product: Product
    cadence: Cadence
    snapshot: InsightsSnapshot
    strategy: ProductStrategyHold


@dataclass
class LoadDigestData:
    """Load BigQuery (or fixture) Snapshot + strategy hold together."""

    snapshots: SnapshotRepository
    strategies: StrategyRepository

    def execute(
        self,
        product: Product | str = Product.KIH,
        cadence: Cadence | str = Cadence.WEEKLY,
    ) -> DigestContext:
        product = Product(product)
        cadence = Cadence(cadence)
        snapshot = self.snapshots.get_latest(product, cadence)
        strategy = self.strategies.get(product, cadence)
        return DigestContext(
            product=product,
            cadence=cadence,
            snapshot=snapshot,
            strategy=strategy,
        )
