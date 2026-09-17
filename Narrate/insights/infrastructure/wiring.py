"""Wire adapters from env."""

from __future__ import annotations

import os

from insights.application.refresh_strategy import SnapshotStrategyRefresher
from insights.domain.models import DeliveryChannel
from insights.domain.ports import (
    DigestEnricher,
    DigestNotifier,
    SnapshotRepository,
    StrategyRefresher,
    StrategyRepository,
)
from insights.infrastructure.bq_snapshot_repo import BigQuerySnapshotRepository
from insights.infrastructure.bq_strategy_repo import BigQueryStrategyRepository
from insights.infrastructure.email_notifier import EmailNotifier
from insights.infrastructure.fixture_snapshot_repo import FixtureSnapshotRepository
from insights.infrastructure.fixture_strategy_repo import FixtureStrategyRepository
from insights.infrastructure.gemini_client import gemini_configured
from insights.infrastructure.gemini_enricher import GeminiEnricher
from insights.infrastructure.gemini_strategy_refresher import GeminiStrategyRefresher
from insights.infrastructure.noop_enricher import NoopEnricher
from insights.infrastructure.slack_notifier import SlackNotifier


def _genai_enabled() -> bool:
    """DIGEST_GENAI=0 forces noop/template; default on when key present."""
    flag = os.getenv("DIGEST_GENAI", "1").strip()
    return flag != "0" and gemini_configured()


def build_snapshot_repo() -> SnapshotRepository:
    use_fixture = os.getenv("DIGEST_USE_FIXTURE", "1") == "1"
    if use_fixture:
        return FixtureSnapshotRepository()
    return BigQuerySnapshotRepository()


def build_strategy_repo() -> StrategyRepository:
    use_fixture = os.getenv("DIGEST_USE_FIXTURE", "1") == "1"
    if use_fixture:
        return FixtureStrategyRepository()
    return BigQueryStrategyRepository()


def build_enricher() -> DigestEnricher:
    if _genai_enabled():
        return GeminiEnricher()
    return NoopEnricher()


def build_strategy_refresher() -> StrategyRefresher:
    if _genai_enabled():
        return GeminiStrategyRefresher()
    return SnapshotStrategyRefresher()


def build_notifier() -> DigestNotifier:
    """Default: email. Set DIGEST_CHANNEL=slack when ready."""
    raw = os.getenv("DIGEST_CHANNEL", DeliveryChannel.EMAIL.value).strip().lower()
    try:
        channel = DeliveryChannel(raw)
    except ValueError:
        channel = DeliveryChannel.EMAIL

    if channel is DeliveryChannel.SLACK:
        return SlackNotifier()
    return EmailNotifier()
