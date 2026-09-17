"""Per-product Digest facts pack from marts / core (reuse executive query patterns)."""

from __future__ import annotations

from typing import Any

from insights.application.executive_layer import (
    _mart_metrics,
    _query_maps,
    _trim_product_mart,
)
from insights.domain.models import Cadence, Product
from insights.integrations.bigquery.client import get_bigquery_client
from insights.integrations.bigquery.config import BigQueryConfig
from insights.integrations.products import PRODUCT_SOURCES


def lookback_for_cadence(cadence: Cadence | str) -> int:
    c = Cadence(cadence)
    if c is Cadence.MONTHLY:
        return 30
    return 7


def gather_product_facts(
    product: Product | str,
    *,
    lookback_days: int = 7,
) -> dict[str, Any]:
    """
    Pull latest finalized marts (+ optional top cloud services / executive)
    for one product. Fail-open: missing tables → omit keys.
    """
    product = Product(product)
    cfg = BigQueryConfig.from_env()
    client = get_bigquery_client(cfg.project)
    p = product.value

    snapshots = _query_maps(
        client,
        cfg,
        f"""
        SELECT product, period_date, sessions, users, sessions_delta_pct,
               cloud_cost_usd, cloud_cost_delta_pct, ai_cost_usd,
               reliability_flags, watch_bullets
        FROM `{cfg.project}.marts_insights.snapshot_daily`
        WHERE product = '{p}'
        QUALIFY ROW_NUMBER() OVER (ORDER BY period_date DESC) = 1
        """,
    )
    growth = _mart_metrics(client, cfg, "growth")
    product_m = _mart_metrics(client, cfg, "product")
    customer = _mart_metrics(client, cfg, "customer")
    ai = _mart_metrics(client, cfg, "ai")
    cost = _mart_metrics(client, cfg, "cost")
    reliability = _mart_metrics(client, cfg, "reliability")

    pack: dict[str, Any] = {
        "product": p,
        "display_name": PRODUCT_SOURCES[product].display_name,
        "lookback_days": lookback_days,
        "snapshot": snapshots.get(p),
        "marts": {
            "growth": growth.get(p),
            "product": _trim_product_mart(product_m.get(p)),
            "customer": customer.get(p),
            "ai": ai.get(p),
            "cost": cost.get(p),
            "reliability": reliability.get(p),
        },
        "top_cloud_services": _top_cloud_services(client, cfg, p, lookback_days),
        "executive": _product_executive(client, cfg, p),
    }
    return pack


def curated_kpi_lines(facts: dict[str, Any] | None) -> list[str]:
    """Short KPI extras for the email (not a BQ dump)."""
    if not facts:
        return []
    lines: list[str] = []
    marts = facts.get("marts") or {}

    product_m = (marts.get("product") or {}).get("metrics") or {}
    top = product_m.get("top_events") or []
    if top:
        bits = []
        for ev in top[:3]:
            name = ev.get("event_name") or ev.get("name") or "?"
            cnt = ev.get("event_count") or ev.get("count")
            bits.append(f"{name}×{cnt}" if cnt is not None else str(name))
        lines.append("Top events: " + ", ".join(bits))
    elif product_m.get("event_total") is not None:
        lines.append(f"Events: {product_m['event_total']}")

    ai = (marts.get("ai") or {}).get("metrics") or {}
    if ai:
        traces = ai.get("trace_count")
        cost = ai.get("total_cost_usd")
        if traces is not None:
            cost_s = f"${cost:,.2f}" if isinstance(cost, (int, float)) else "n/a"
            note = ""
            if isinstance(traces, (int, float)) and traces > 0 and (not cost or cost == 0):
                note = " (pricing unset?)"
            lines.append(f"AI traces: {traces}, AI $: {cost_s}{note}")

    rel = (marts.get("reliability") or {}).get("metrics") or {}
    if rel:
        up = rel.get("services_up")
        total = rel.get("services_total")
        down = rel.get("services_down")
        if up is not None or total is not None:
            lines.append(
                f"Services: {up if up is not None else '?'}"
                f"/{total if total is not None else '?'} up"
                + (f" ({down} down)" if down else "")
            )
        failing = rel.get("failing") or []
        if failing:
            names = [
                (f.get("service") or f.get("name") or str(f))
                if isinstance(f, dict)
                else str(f)
                for f in failing[:2]
            ]
            lines.append("Failing: " + ", ".join(names))

    customer = (marts.get("customer") or {}).get("metrics") or {}
    if customer.get("dau") is not None:
        lines.append(f"DAU: {customer['dau']}")

    top_svc = facts.get("top_cloud_services") or []
    if top_svc:
        bits = [
            f"{s.get('service_name', '?')} ${s.get('cost_usd', 0):,.2f}"
            for s in top_svc[:3]
        ]
        lines.append("Top cloud: " + "; ".join(bits))

    return lines[:4]


def action_lines(facts: dict[str, Any] | None) -> list[str]:
    """
    Deterministic owner actions from existing marts/executive (no GenAI).
    Order: executive priority → reliability → AI cost gap → top cloud → top event.
    """
    if not facts:
        return []
    actions: list[str] = []
    marts = facts.get("marts") or {}

    executive = facts.get("executive") or {}
    for prio in (executive.get("priorities") or [])[:1]:
        if not isinstance(prio, dict):
            continue
        action = (prio.get("action") or "").strip()
        rationale = (prio.get("rationale") or "").strip()
        if action:
            line = action
            if rationale:
                line = f"{action} — {rationale}"
            actions.append(line)

    rel = (marts.get("reliability") or {}).get("metrics") or {}
    failing = rel.get("failing") or []
    down = rel.get("services_down")
    if failing or (isinstance(down, (int, float)) and down > 0):
        names = [
            (f.get("service") or f.get("name") or str(f))
            if isinstance(f, dict)
            else str(f)
            for f in failing[:2]
        ]
        if names:
            actions.append("Restore failing services: " + ", ".join(names))
        elif down:
            actions.append(f"Investigate {int(down)} service(s) down")

    ai = (marts.get("ai") or {}).get("metrics") or {}
    traces = ai.get("trace_count")
    cost = ai.get("total_cost_usd")
    if (
        isinstance(traces, (int, float))
        and traces > 0
        and (cost is None or float(cost) == 0)
    ):
        actions.append(
            f"Enable Langfuse model pricing ({int(traces)} traces, AI $0)"
        )

    top_svc = facts.get("top_cloud_services") or []
    if top_svc:
        s0 = top_svc[0]
        name = s0.get("service_name") or "?"
        usd = s0.get("cost_usd")
        if isinstance(usd, (int, float)) and usd > 0:
            actions.append(f"Review top cloud burn: {name} (${usd:,.2f} lookback)")

    product_m = (marts.get("product") or {}).get("metrics") or {}
    top = product_m.get("top_events") or []
    if top and isinstance(top[0], dict):
        ev = top[0]
        ename = ev.get("event_name") or ev.get("name")
        cnt = ev.get("event_count") or ev.get("count")
        if ename:
            actions.append(
                f"Double-down on top behavior: {ename}"
                + (f" (×{cnt})" if cnt is not None else "")
            )

    # de-dupe while preserving order
    seen: set[str] = set()
    out: list[str] = []
    for a in actions:
        key = a.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(a)
    return out[:4]


def _top_cloud_services(
    client: Any,
    cfg: BigQueryConfig,
    product: str,
    lookback_days: int,
) -> list[dict[str, Any]]:
    sql = f"""
    SELECT
      COALESCE(
        JSON_VALUE(props_json, '$.service_description'),
        REGEXP_EXTRACT(entity_id, r':gcp:(.+)$'),
        entity_id
      ) AS service_name,
      ROUND(SUM(cost_usd), 2) AS cost_usd
    FROM `{cfg.project}.core.fct_gcp_cost`
    WHERE product = '{product}'
      AND DATE(event_ts) >= DATE_SUB(CURRENT_DATE(), INTERVAL {int(lookback_days)} DAY)
    GROUP BY 1
    ORDER BY cost_usd DESC
    LIMIT 3
    """
    try:
        rows = []
        for r in client.query(sql, location=cfg.location).result():
            rows.append(
                {
                    "service_name": r["service_name"] or "unknown",
                    "cost_usd": float(r["cost_usd"] or 0),
                }
            )
        return rows
    except Exception as exc:
        print(f"digest top_cloud_services failed: {exc}")
        return []


def _product_executive(
    client: Any,
    cfg: BigQueryConfig,
    product: str,
) -> dict[str, Any] | None:
    """Latest portfolio executive row — extract priorities/risks for this product."""
    sql = f"""
    SELECT period_date, metrics_json
    FROM `{cfg.project}.marts.executive`
    WHERE product = 'portfolio'
    ORDER BY period_date DESC
    LIMIT 1
    """
    try:
        rows = list(client.query(sql, location=cfg.location).result())
        if not rows:
            return None
        mj = rows[0]["metrics_json"]
        if hasattr(mj, "items"):
            mj = dict(mj)
        elif isinstance(mj, str):
            import json

            mj = json.loads(mj)
        priorities = [
            p
            for p in (mj.get("priorities") or [])
            if isinstance(p, dict) and (p.get("product") or "").lower() == product
        ]
        risks = [
            r
            for r in (mj.get("risks") or [])
            if isinstance(r, str) and product.lower() in r.lower()
        ]
        if not priorities and not risks:
            return None
        return {"priorities": priorities[:3], "risks": risks[:3]}
    except Exception as exc:
        print(f"digest executive lookup failed: {exc}")
        return None
