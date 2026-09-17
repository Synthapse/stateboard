"""No-op enricher — still attaches BigQuery Snapshot + marts details."""

from __future__ import annotations

from typing import Any

from insights.application.bq_details import snapshot_details
from insights.domain.models import Enrichment, InsightsSnapshot, ProductStrategyHold


class NoopEnricher:
    def enrich(
        self,
        snapshot: InsightsSnapshot,
        strategy: ProductStrategyHold | None = None,
        facts: dict[str, Any] | None = None,
    ) -> Enrichment:
        return Enrichment(details=snapshot_details(snapshot, facts))
