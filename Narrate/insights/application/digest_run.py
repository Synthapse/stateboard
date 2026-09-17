"""Use case: run one Digest for a product × cadence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from insights.application.digest_facts import gather_product_facts, lookback_for_cadence
from insights.application.load_digest_data import LoadDigestData
from insights.application.refresh_strategy import SnapshotStrategyRefresher
from insights.application.render_digest import digest_subject, render_digest
from insights.domain.models import Cadence, Product
from insights.domain.ports import (
    DigestEnricher,
    DigestNotifier,
    SnapshotRepository,
    StrategyRefresher,
    StrategyRepository,
)
from insights.infrastructure.noop_enricher import NoopEnricher


@dataclass
class DigestRunUseCase:
    snapshots: SnapshotRepository
    strategies: StrategyRepository
    notifier: DigestNotifier
    enricher: DigestEnricher | None = None
    refresher: StrategyRefresher | None = None

    def execute(
        self,
        product: Product | str = Product.KIH,
        cadence: Cadence | str = Cadence.WEEKLY,
    ) -> dict[str, Any]:
        enricher = self.enricher or NoopEnricher()
        refresher = self.refresher or SnapshotStrategyRefresher()

        ctx = LoadDigestData(self.snapshots, self.strategies).execute(product, cadence)
        facts: dict[str, Any] = {}
        try:
            import os

            if os.getenv("DIGEST_USE_FIXTURE", "1") != "1":
                facts = gather_product_facts(
                    ctx.product,
                    lookback_days=lookback_for_cadence(ctx.cadence),
                )
        except Exception as exc:
            print(f"digest facts pack failed ({exc}); continuing without marts extras")
            facts = {}
        enrichment = enricher.enrich(ctx.snapshot, ctx.strategy, facts=facts or None)
        hold = refresher.refresh(ctx.strategy, ctx.snapshot, enrichment)
        self.strategies.upsert(hold)

        body = render_digest(
            ctx.snapshot,
            ctx.cadence,
            strategy=hold,
            enrichment=enrichment,
            facts=facts,
        )
        subject = digest_subject(ctx.snapshot, ctx.cadence)
        from insights.infrastructure.email_notifier import audience_for

        audience = audience_for(ctx.product.value)
        sent = self.notifier.send(
            subject=subject,
            body=body,
            product=ctx.product.value,
            cadence=ctx.cadence.value,
            period_date=str(ctx.snapshot.period_date),
        )
        return {
            "product": ctx.product.value,
            "cadence": ctx.cadence.value,
            "schema_version": ctx.snapshot.schema_version,
            "period_date": str(ctx.snapshot.period_date),
            "channel": self.notifier.channel,
            "audience": audience,
            "delivered": sent,
            "subject": subject,
            "enriched": bool(
                enrichment.executive_skim
                or enrichment.watch_bullets
                or enrichment.insights
            ),
            "insights": len(enrichment.insights),
            "bq_details": len(enrichment.details),
            "strategy_title": hold.title,
            "strategy_refreshed_by": hold.refreshed_by,
            "strategy_updated_at": hold.updated_at.isoformat() if hold.updated_at else None,
            "text": body,
        }
