"""Pure render: Snapshot (+ strategy + enrichment + curated facts) → Digest text."""

from __future__ import annotations

from typing import Any

from insights.application.digest_facts import action_lines, curated_kpi_lines
from insights.domain.models import Cadence, Enrichment, InsightsSnapshot, ProductStrategyHold


def _pct(v: float | None) -> str:
    if v is None:
        return "n/a"
    sign = "+" if v > 0 else ""
    return f"{sign}{v:.1f}%"


def _money(v: float | None) -> str:
    if v is None:
        return "n/a"
    return f"${v:,.2f}"


def _num(v: int | None) -> str:
    if v is None:
        return "n/a"
    return f"{v:,}"


def digest_subject(
    snapshot: InsightsSnapshot,
    cadence: Cadence = Cadence.WEEKLY,
) -> str:
    """Short subject: [KIH] Sessions +0.0% · Cloud $0.00"""
    product = snapshot.product.value.upper()
    return (
        f"[{product}] Sessions {_pct(snapshot.sessions_delta_pct)} · "
        f"Cloud {_money(snapshot.cloud_cost_usd)}"
    )


def render_digest(
    snapshot: InsightsSnapshot,
    cadence: Cadence = Cadence.WEEKLY,
    strategy: ProductStrategyHold | None = None,
    enrichment: Enrichment | None = None,
    facts: dict[str, Any] | None = None,
) -> str:
    period = (
        f"{snapshot.period_start.date() if snapshot.period_start else '?'} → "
        f"{snapshot.period_end.date() if snapshot.period_end else snapshot.period_date}"
    )
    lines = [
        f"{snapshot.product.value.upper()} {cadence.value} Digest",
        f"Period: {period}",
    ]

    actions = action_lines(facts)
    if actions:
        lines.append("")
        lines.append("Actions")
        for a in actions:
            lines.append(f"• {a}")

    lines.extend(
        [
            "",
            f"• Sessions: {_num(snapshot.sessions)} ({_pct(snapshot.sessions_delta_pct)} vs prior)",
            f"• Users: {_num(snapshot.users)}",
            f"• Cloud $: {_money(snapshot.cloud_cost_usd)} ({_pct(snapshot.cloud_cost_delta_pct)})",
            f"• AI $: {_money(snapshot.ai_cost_usd)}",
        ]
    )

    for extra in curated_kpi_lines(facts):
        lines.append(f"• {extra}")

    if snapshot.reliability_flags:
        lines.append("")
        lines.append("Reliability")
        for flag in snapshot.reliability_flags[:3]:
            lines.append(f"• {flag}")

    insights = enrichment.insights if enrichment and enrichment.insights else []
    if insights:
        lines.append("")
        lines.append("Insights")
        for bullet in insights[:3]:
            lines.append(f"• {bullet}")

    watch = (
        enrichment.watch_bullets
        if enrichment and enrichment.watch_bullets
        else snapshot.watch_bullets
    )
    # Skip executive_skim when Insights present (avoid duplicate narrative)
    skim = enrichment.executive_skim.strip() if enrichment and enrichment.executive_skim else ""
    if skim and not insights:
        lines.append("")
        lines.append("Executive skim")
        lines.append(skim)

    if watch:
        lines.append("")
        lines.append("What to watch")
        for bullet in watch[:3]:
            lines.append(f"• {bullet}")

    if strategy:
        lines.append("")
        lines.append(f"Strategy hold — {strategy.title}")
        risk = strategy.risk_mitigation
        if risk.content:
            lines.append(f"Risk: {risk.content}")
        if risk.subsections:
            for sub in risk.subsections[:2]:
                lines.append(f"  – {sub.title}: {sub.content}")

    return "\n".join(lines)
