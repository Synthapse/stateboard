"""StrategyRepository adapter → BigQueryStrategyLoader integration."""

from __future__ import annotations

from insights.application.normalize_gtm import ensure_hold_subsections
from insights.domain.models import Cadence, Product, ProductStrategyHold
from insights.infrastructure.fixture_strategy_repo import FixtureStrategyRepository
from insights.integrations.bigquery.config import BigQueryConfig
from insights.integrations.bigquery.strategy_loader import BigQueryStrategyLoader


class BigQueryStrategyRepository:
    def __init__(self, config: BigQueryConfig | None = None) -> None:
        self._loader = BigQueryStrategyLoader(config)
        self._fallback = FixtureStrategyRepository()

    def get(self, product: Product, cadence: Cadence) -> ProductStrategyHold:
        try:
            return ensure_hold_subsections(self._loader.load_latest(product, cadence))
        except Exception as exc:
            print(f"BQ strategy load failed ({exc}); using fixture")
            return self._fallback.get(product, cadence)

    def upsert(self, hold: ProductStrategyHold) -> None:
        hold = ensure_hold_subsections(hold)
        try:
            self._loader.save(hold)
        except Exception as exc:
            print(f"BQ strategy upsert failed ({exc}); writing fixture store")
            self._fallback.upsert(hold)
