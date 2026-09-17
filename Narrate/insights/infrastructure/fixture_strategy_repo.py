"""Fixture-backed StrategyRepository (local / DIGEST_USE_FIXTURE=1)."""

from __future__ import annotations

import json
from pathlib import Path

from insights.application.normalize_gtm import ensure_hold_subsections
from insights.domain.models import Cadence, Product, ProductStrategyHold

_FIXTURES = Path(__file__).parent / "fixtures"
_STORE = Path(__file__).parent / "fixtures" / "_strategy_store"


class FixtureStrategyRepository:
    """Seed JSON + local upsert store; always normalizes subsections on read."""

    def __init__(self) -> None:
        _STORE.mkdir(parents=True, exist_ok=True)

    def get(self, product: Product, cadence: Cadence) -> ProductStrategyHold:
        stored = _STORE / f"{product.value}_{cadence.value}.json"
        path = stored if stored.exists() else _FIXTURES / f"strategy_{product.value}.json"
        if not path.exists():
            raise FileNotFoundError(f"No strategy fixture for {product.value}: {path.name}")
        data = json.loads(path.read_text())
        data.setdefault("product", product.value)
        data.setdefault("cadence", cadence.value)
        return ensure_hold_subsections(ProductStrategyHold.model_validate(data))

    def upsert(self, hold: ProductStrategyHold) -> None:
        hold = ensure_hold_subsections(hold)
        path = _STORE / f"{hold.product.value}_{hold.cadence.value}.json"
        path.write_text(hold.model_dump_json(indent=2))
