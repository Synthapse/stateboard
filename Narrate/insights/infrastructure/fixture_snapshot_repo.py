"""Fixture-backed SnapshotRepository (local / DIGEST_USE_FIXTURE=1)."""

from __future__ import annotations

import json
from pathlib import Path

from insights.domain.models import Cadence, InsightsSnapshot, Product

_FIXTURES = Path(__file__).parent / "fixtures"


class FixtureSnapshotRepository:
    def get_latest(self, product: Product, cadence: Cadence) -> InsightsSnapshot:
        path = _FIXTURES / f"{product.value}_{cadence.value}.json"
        if not path.exists():
            raise FileNotFoundError(
                f"No fixture for {product.value}/{cadence.value}: expected {path.name}"
            )
        return InsightsSnapshot.model_validate(json.loads(path.read_text()))
