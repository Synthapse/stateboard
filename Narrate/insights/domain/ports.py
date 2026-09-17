"""Ports (interfaces) — infrastructure implements these."""

from __future__ import annotations

from typing import Any, Protocol

from insights.domain.models import (
    Cadence,
    Enrichment,
    InsightsSnapshot,
    Product,
    ProductStrategyHold,
)


class SnapshotRepository(Protocol):
    def get_latest(self, product: Product, cadence: Cadence) -> InsightsSnapshot: ...


class StrategyRepository(Protocol):
    """Living GTM-style holds per product — read + write each Digest cadence."""

    def get(self, product: Product, cadence: Cadence) -> ProductStrategyHold: ...

    def upsert(self, hold: ProductStrategyHold) -> None: ...


class DigestNotifier(Protocol):
    """Deliver rendered Digest text to an inbox channel."""

    channel: str

    def send(
        self,
        subject: str,
        body: str,
        *,
        product: str | None = None,
        cadence: str | None = None,
        period_date: str | None = None,
    ) -> bool:
        """Return True if delivered, False if skipped (misconfigured)."""
        ...


class DigestEnricher(Protocol):
    def enrich(
        self,
        snapshot: InsightsSnapshot,
        strategy: ProductStrategyHold | None = None,
        facts: dict[str, Any] | None = None,
    ) -> Enrichment: ...


class StrategyRefresher(Protocol):
    """Edit strategy hold from this cadence's Snapshot (+ optional Enrichment)."""

    def refresh(
        self,
        hold: ProductStrategyHold,
        snapshot: InsightsSnapshot,
        enrichment: Enrichment | None = None,
    ) -> ProductStrategyHold: ...
