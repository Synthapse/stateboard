"""Build Enrichment.details from Snapshot + optional marts facts pack."""

from __future__ import annotations

from typing import Any

from insights.domain.models import InsightsSnapshot, MetricDetail

_SNAP = "marts_insights.snapshot_daily"


def _pct(v: float | None) -> str:
    if v is None:
        return "n/a"
    sign = "+" if v > 0 else ""
    return f"{sign}{v:.1f}%"


def _money(v: float | None) -> str:
    if v is None:
        return "n/a"
    return f"${v:,.2f}"


def _num(v: int | float | None) -> str:
    if v is None:
        return "n/a"
    if isinstance(v, float) and not v.is_integer():
        return f"{v:,.2f}"
    return f"{int(v):,}"


def snapshot_details(
    snapshot: InsightsSnapshot,
    facts: dict[str, Any] | None = None,
) -> list[MetricDetail]:
    """Deterministic BQ facts — GenAI must cite these, never invent replacements."""
    details = [
        MetricDetail(label="product", value=snapshot.product.value, source=_SNAP),
        MetricDetail(label="period_date", value=str(snapshot.period_date), source=_SNAP),
        MetricDetail(label="sessions", value=_num(snapshot.sessions), source=_SNAP),
        MetricDetail(
            label="sessions_delta_pct",
            value=_pct(snapshot.sessions_delta_pct),
            source=_SNAP,
        ),
        MetricDetail(label="users", value=_num(snapshot.users), source=_SNAP),
        MetricDetail(
            label="cloud_cost_usd",
            value=_money(snapshot.cloud_cost_usd),
            source=_SNAP,
        ),
        MetricDetail(
            label="cloud_cost_delta_pct",
            value=_pct(snapshot.cloud_cost_delta_pct),
            source=_SNAP,
        ),
        MetricDetail(label="ai_cost_usd", value=_money(snapshot.ai_cost_usd), source=_SNAP),
    ]
    if snapshot.period_start:
        details.append(
            MetricDetail(
                label="period_start",
                value=str(snapshot.period_start.date()),
                source=_SNAP,
            )
        )
    if snapshot.period_end:
        details.append(
            MetricDetail(
                label="period_end",
                value=str(snapshot.period_end.date()),
                source=_SNAP,
            )
        )
    for i, flag in enumerate(snapshot.reliability_flags[:3]):
        details.append(
            MetricDetail(label=f"reliability_flag_{i+1}", value=flag, source=_SNAP)
        )

    details.extend(_facts_details(facts))
    return details


def _facts_details(facts: dict[str, Any] | None) -> list[MetricDetail]:
    if not facts:
        return []
    out: list[MetricDetail] = []
    marts = facts.get("marts") or {}

    product_m = (marts.get("product") or {}).get("metrics") or {}
    if product_m.get("event_total") is not None:
        out.append(
            MetricDetail(
                label="event_total",
                value=_num(product_m["event_total"]),
                source="marts.product",
            )
        )
    for i, ev in enumerate((product_m.get("top_events") or [])[:3]):
        if not isinstance(ev, dict):
            continue
        name = ev.get("event_name") or ev.get("name") or f"event_{i+1}"
        cnt = ev.get("event_count") or ev.get("count")
        users = ev.get("users")
        val = f"{name} count={_num(cnt)}"
        if users is not None:
            val += f" users={_num(users)}"
        out.append(
            MetricDetail(label=f"top_event_{i+1}", value=val, source="marts.product")
        )

    customer = (marts.get("customer") or {}).get("metrics") or {}
    if customer.get("dau") is not None:
        out.append(
            MetricDetail(label="dau", value=_num(customer["dau"]), source="marts.customer")
        )
    if customer.get("active_days_7d") is not None:
        out.append(
            MetricDetail(
                label="active_days_7d",
                value=_num(customer["active_days_7d"]),
                source="marts.customer",
            )
        )
    if customer.get("wau_engagement_sum") is not None:
        out.append(
            MetricDetail(
                label="engagement_proxy_7d",
                value=_num(customer["wau_engagement_sum"]),
                source="marts.customer",
            )
        )

    ai = (marts.get("ai") or {}).get("metrics") or {}
    if ai.get("trace_count") is not None:
        out.append(
            MetricDetail(
                label="ai_trace_count",
                value=_num(ai["trace_count"]),
                source="marts.ai",
            )
        )
    if ai.get("total_cost_usd") is not None:
        out.append(
            MetricDetail(
                label="ai_total_cost_usd",
                value=_money(float(ai["total_cost_usd"])),
                source="marts.ai",
            )
        )
    traces = ai.get("trace_count")
    cost = ai.get("total_cost_usd")
    if (
        isinstance(traces, (int, float))
        and traces > 0
        and (cost is None or float(cost) == 0)
    ):
        out.append(
            MetricDetail(
                label="ai_cost_gap",
                value="traces>0 but AI cost is $0 — Langfuse pricing may be unset",
                source="marts.ai",
            )
        )

    rel = (marts.get("reliability") or {}).get("metrics") or {}
    if rel.get("services_up") is not None or rel.get("services_total") is not None:
        out.append(
            MetricDetail(
                label="services_up_total",
                value=f"{rel.get('services_up', '?')}/{rel.get('services_total', '?')}",
                source="marts.reliability",
            )
        )
    if rel.get("services_down") is not None:
        out.append(
            MetricDetail(
                label="services_down",
                value=_num(rel["services_down"]),
                source="marts.reliability",
            )
        )
    if rel.get("exception_count") is not None:
        out.append(
            MetricDetail(
                label="exception_count",
                value=_num(rel["exception_count"]),
                source="marts.reliability",
            )
        )
    if rel.get("avg_latency_ms") is not None:
        out.append(
            MetricDetail(
                label="avg_latency_ms",
                value=_num(rel["avg_latency_ms"]),
                source="marts.reliability",
            )
        )
    for i, f in enumerate((rel.get("failing") or [])[:3]):
        name = f.get("service") or f.get("name") if isinstance(f, dict) else str(f)
        out.append(
            MetricDetail(
                label=f"failing_service_{i+1}",
                value=str(name),
                source="marts.reliability",
            )
        )

    for i, s in enumerate((facts.get("top_cloud_services") or [])[:3]):
        if not isinstance(s, dict):
            continue
        out.append(
            MetricDetail(
                label=f"top_cloud_service_{i+1}",
                value=f"{s.get('service_name', '?')} {_money(s.get('cost_usd'))}",
                source="core.fct_gcp_cost",
            )
        )

    executive = facts.get("executive") or {}
    for i, prio in enumerate((executive.get("priorities") or [])[:2]):
        if not isinstance(prio, dict):
            continue
        action = prio.get("action") or ""
        rationale = prio.get("rationale") or ""
        out.append(
            MetricDetail(
                label=f"executive_priority_{i+1}",
                value=f"{action} — {rationale}".strip(" —"),
                source="marts.executive",
            )
        )
    for i, risk in enumerate((executive.get("risks") or [])[:2]):
        out.append(
            MetricDetail(
                label=f"executive_risk_{i+1}",
                value=str(risk),
                source="marts.executive",
            )
        )

    return out
