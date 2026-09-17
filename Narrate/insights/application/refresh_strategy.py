"""Refresh ProductStrategyHold from Snapshot (template; always keeps subsections)."""

from __future__ import annotations

from datetime import datetime, timezone

from document.MultiAgent.gtm_structure import GTMSection
from insights.application.normalize_gtm import SECTION_SUBSECTION_HINTS, ensure_hold_subsections
from insights.domain.models import Enrichment, InsightsSnapshot, ProductStrategyHold


class SnapshotStrategyRefresher:
    """Edits the living GTMStrategy-based hold each Digest run (no Gemini)."""

    def refresh(
        self,
        hold: ProductStrategyHold,
        snapshot: InsightsSnapshot,
        enrichment: Enrichment | None = None,
    ) -> ProductStrategyHold:
        product = snapshot.product.value.upper()
        bullets = (
            enrichment.watch_bullets
            if enrichment and enrichment.watch_bullets
            else snapshot.watch_bullets
        )
        insights = enrichment.insights if enrichment and enrichment.insights else []

        delta = (
            f"{snapshot.sessions_delta_pct:+.1f}%"
            if snapshot.sessions_delta_pct is not None
            else "n/a"
        )
        cost = (
            f"${snapshot.cloud_cost_usd:,.2f}"
            if snapshot.cloud_cost_usd is not None
            else "n/a"
        )

        # Do not paste enrichment.executive_skim (avoids duplicate email narrative).
        bits = [
            f"{product} {hold.cadence.value} refresh ({snapshot.period_date}).",
            f"Sessions {snapshot.sessions or 'n/a'} ({delta} vs prior); cloud {cost}.",
        ]
        if insights:
            bits.append("Focus: " + "; ".join(insights[:2]))
        elif bullets:
            bits.append("Watch: " + "; ".join(bullets[:3]))

        hold.executive_summary = " ".join(bits)
        hold.period_date = snapshot.period_date
        hold.updated_at = datetime.now(timezone.utc)
        hold.refreshed_by = "digest_run"

        if snapshot.reliability_flags:
            flags = "; ".join(snapshot.reliability_flags[:3])
            h = SECTION_SUBSECTION_HINTS["risk_mitigation"]
            hold.risk_mitigation = GTMSection(
                title="Risk mitigation",
                content="Reliability signals from this cadence Snapshot.",
                subsections=[
                    GTMSection(title=h[0], content=f"Active: {flags}"),
                    GTMSection(
                        title=h[1],
                        content="Keep watching until cleared; escalate if still open next cadence.",
                    ),
                    GTMSection(
                        title=h[2],
                        content="Owner: Digest run — re-check next weekly/monthly.",
                    ),
                ],
            )

        if snapshot.cloud_cost_usd is not None:
            h = SECTION_SUBSECTION_HINTS["budget_forecast"]
            delta_txt = (
                f"{snapshot.cloud_cost_delta_pct:+.1f}% vs prior"
                if snapshot.cloud_cost_delta_pct is not None
                else "delta n/a"
            )
            ai_txt = (
                f"AI ${snapshot.ai_cost_usd:,.2f}"
                if snapshot.ai_cost_usd is not None
                else "AI n/a"
            )
            hold.budget_forecast = GTMSection(
                title="Budget forecast",
                content="Spend signals from Snapshot (not invented).",
                subsections=[
                    GTMSection(title=h[0], content=f"Cloud {cost} ({delta_txt}); {ai_txt}."),
                    GTMSection(
                        title=h[1],
                        content="Flag if cloud + AI rise while sessions fall.",
                    ),
                ],
            )

        return ensure_hold_subsections(hold)
