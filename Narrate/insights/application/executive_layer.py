"""Portfolio GenAI executive layer — consume finalized marts/snapshots → marts.executive."""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from typing import Any

from insights.domain.models import Product
from insights.integrations.bigquery.client import get_bigquery_client
from insights.integrations.bigquery.config import BigQueryConfig
from insights.integrations.products import PRODUCT_SOURCES

_SYSTEM = (
    "You are a portfolio COO for three products: kih (Dr Kiwi), lindle, yca (CzatBudowlany). "
    "You receive ONLY finalized warehouse facts (snapshots + marts). "
    "Never invent metrics — cite numbers from the facts pack only. "
    "Output JSON only with keys: "
    "executive_summary (string, 120-180 words), "
    "direction (string, 1-2 sentences on portfolio trajectory), "
    "priorities (array of up to 5 objects: "
    "{rank:int, product:string, action:string, rationale:string, facts:string[]}), "
    "risks (array of up to 3 strings, each citing a fact). "
    "Prioritize by: reliability fails first, then growth stagnation, then cost/AI burn, "
    "then missing data that blocks decisions. Be concrete and actionable."
)


def gather_facts_pack() -> dict[str, Any]:
    """Pull latest finalized facts per product from BQ (no live GA4/Langfuse calls)."""
    cfg = BigQueryConfig.from_env()
    client = get_bigquery_client(cfg.project)
    products = [p.value for p in Product]

    snapshots = _query_maps(
        client,
        cfg,
        f"""
        SELECT product, period_date, sessions, users, sessions_delta_pct,
               cloud_cost_usd, cloud_cost_delta_pct, ai_cost_usd,
               reliability_flags, watch_bullets
        FROM `{cfg.project}.marts_insights.snapshot_daily`
        QUALIFY ROW_NUMBER() OVER (PARTITION BY product ORDER BY period_date DESC) = 1
        """,
    )
    growth = _mart_metrics(client, cfg, "growth")
    product_m = _mart_metrics(client, cfg, "product")
    customer = _mart_metrics(client, cfg, "customer")
    ai = _mart_metrics(client, cfg, "ai")
    cost = _mart_metrics(client, cfg, "cost")
    reliability = _mart_metrics(client, cfg, "reliability")

    pack: dict[str, Any] = {
        "as_of": date.today().isoformat(),
        "products": {},
    }
    for p in products:
        pack["products"][p] = {
            "display_name": PRODUCT_SOURCES[Product(p)].display_name,
            "snapshot": snapshots.get(p),
            "marts": {
                "growth": growth.get(p),
                "product": _trim_product_mart(product_m.get(p)),
                "customer": customer.get(p),
                "ai": ai.get(p),
                "cost": cost.get(p),
                "reliability": reliability.get(p),
            },
        }
    return pack


def run_executive_layer(*, send_email: bool = False) -> dict[str, Any]:
    """
    GenAI aggregation layer:
      facts pack (BQ) → Gemini executive summary + priorities → marts.executive
    Fail-open: if Gemini off/fails, still write a facts-only stub.
    """
    cfg = BigQueryConfig.from_env()
    client = get_bigquery_client(cfg.project)
    now = datetime.now(timezone.utc)
    today = date.today().isoformat()
    facts = gather_facts_pack()

    narrative = _generate_narrative(facts)
    metrics = {
        "executive_summary": narrative.get("executive_summary") or "",
        "direction": narrative.get("direction") or "",
        "priorities": narrative.get("priorities") or [],
        "risks": narrative.get("risks") or [],
        "facts_pack": facts,
        "model": narrative.get("model"),
        "source": narrative.get("source"),
    }

    row = {
        "period_date": today,
        "product": "portfolio",
        "cadence": "daily",
        "metrics_json": metrics,
        "updated_at": now.isoformat(),
    }
    upsert = _upsert_executive(client, cfg, row)

    # Optional per-product skim rows (priority slice for that product)
    per_product_rows = []
    for pr in metrics.get("priorities") or []:
        prod = pr.get("product")
        if not prod or prod == "portfolio":
            continue
        per_product_rows.append(
            {
                "period_date": today,
                "product": prod,
                "cadence": "daily",
                "metrics_json": {
                    "executive_summary": metrics["executive_summary"],
                    "direction": metrics["direction"],
                    "priority": pr,
                    "risks": [r for r in (metrics.get("risks") or []) if prod in r.lower()],
                    "source": metrics.get("source"),
                },
                "updated_at": now.isoformat(),
            }
        )
    if per_product_rows:
        _upsert_executive_batch(client, cfg, per_product_rows)

    result = {
        "status": "ok",
        "period_date": today,
        "product": "portfolio",
        "source": metrics.get("source"),
        "executive_summary": metrics["executive_summary"],
        "direction": metrics["direction"],
        "priorities": metrics["priorities"],
        "risks": metrics["risks"],
        "marts_executive": upsert,
    }

    if send_email:
        result["email"] = _maybe_email(metrics)

    return result


def _generate_narrative(facts: dict[str, Any]) -> dict[str, Any]:
    from insights.infrastructure.gemini_client import gemini_configured, generate_json

    if not gemini_configured():
        return _facts_only_narrative(facts, source="facts_only_no_gemini")

    try:
        raw = generate_json(
            prompt="Portfolio facts pack (warehouse SoT):\n"
            + json.dumps(facts, default=str)[:120000],
            system=_SYSTEM,
        )
        return {
            "executive_summary": str(raw.get("executive_summary") or "").strip(),
            "direction": str(raw.get("direction") or "").strip(),
            "priorities": raw.get("priorities") or [],
            "risks": raw.get("risks") or [],
            "model": __import__("os").getenv("GEMINI_MODEL", "gemini-1.5-flash-latest"),
            "source": "gemini",
        }
    except Exception as exc:
        print(f"Executive Gemini failed ({exc}); facts-only stub")
        return _facts_only_narrative(facts, source=f"facts_only_error:{exc}"[:80])


def _facts_only_narrative(facts: dict[str, Any], *, source: str) -> dict[str, Any]:
    """Deterministic stub when Gemini unavailable — still cites warehouse facts."""
    lines = []
    priorities = []
    risks = []
    rank = 1
    for product, block in (facts.get("products") or {}).items():
        snap = block.get("snapshot") or {}
        rel = ((block.get("marts") or {}).get("reliability") or {}).get("metrics") or {}
        sessions = snap.get("sessions")
        ai = snap.get("ai_cost_usd")
        cloud = snap.get("cloud_cost_usd")
        down = rel.get("services_down") or 0
        failing = rel.get("failing") or []
        lines.append(
            f"{product}: sessions={sessions}, users={snap.get('users')}, "
            f"cloud=${cloud}, ai=${ai}, services_down={down}"
        )
        if down and failing:
            priorities.append(
                {
                    "rank": rank,
                    "product": product,
                    "action": f"Restore failing services: {', '.join(map(str, failing[:3]))}",
                    "rationale": f"{down} service(s) down in marts.reliability",
                    "facts": [f"services_down={down}", f"failing={failing[:3]}"],
                }
            )
            risks.append(f"{product}: reliability fail {failing[:3]}")
            rank += 1
        if (snap.get("ai_cost_usd") == 0) and any(
            "langfuse:traces=" in str(f) for f in (snap.get("reliability_flags") or [])
        ):
            priorities.append(
                {
                    "rank": rank,
                    "product": product,
                    "action": "Enable Langfuse model pricing so AI $ is measurable",
                    "rationale": "Traces present but ai_cost_usd=0 in snapshot",
                    "facts": [f"ai_cost_usd={ai}", f"flags={snap.get('reliability_flags')}"],
                }
            )
            rank += 1
        if cloud in (None, 0) and product != "lindle":
            priorities.append(
                {
                    "rank": rank,
                    "product": product,
                    "action": "Enable GCP Billing export → BigQuery for cloud cost",
                    "rationale": "snapshot cloud_cost_usd is 0 / missing",
                    "facts": [f"cloud_cost_usd={cloud}"],
                }
            )
            rank += 1

    summary = (
        "Portfolio facts (GenAI off). "
        + " | ".join(lines)
        + ". Prioritize reliability restores, then cost visibility, then growth."
    )
    return {
        "executive_summary": summary[:900],
        "direction": "Stabilize reliability and fill cost/AI visibility gaps before scaling growth bets.",
        "priorities": priorities[:5],
        "risks": risks[:3],
        "model": None,
        "source": source,
    }


def _mart_metrics(client: Any, cfg: BigQueryConfig, mart: str) -> dict[str, dict[str, Any]]:
    return _query_maps(
        client,
        cfg,
        f"""
        SELECT product, period_date, metrics_json
        FROM `{cfg.project}.marts.{mart}`
        QUALIFY ROW_NUMBER() OVER (PARTITION BY product ORDER BY period_date DESC) = 1
        """,
        metrics_key="metrics",
    )


def _query_maps(
    client: Any,
    cfg: BigQueryConfig,
    sql: str,
    *,
    metrics_key: str | None = None,
) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    try:
        for r in client.query(sql, location=cfg.location).result():
            d = dict(r)
            product = d.pop("product", None)
            if not product:
                continue
            if metrics_key and "metrics_json" in d:
                mj = d.pop("metrics_json")
                if hasattr(mj, "items"):
                    mj = dict(mj)
                elif isinstance(mj, str):
                    try:
                        mj = json.loads(mj)
                    except Exception:
                        pass
                d[metrics_key] = mj
            # stringify dates
            for k, v in list(d.items()):
                if hasattr(v, "isoformat"):
                    d[k] = v.isoformat()
            out[product] = d
    except Exception as exc:
        print(f"executive facts query failed: {exc}")
    return out


def _trim_product_mart(block: dict[str, Any] | None) -> dict[str, Any] | None:
    if not block:
        return block
    metrics = block.get("metrics") or {}
    top = metrics.get("top_events") or []
    return {
        **{k: v for k, v in block.items() if k != "metrics"},
        "metrics": {
            "event_total": metrics.get("event_total"),
            "event_types": metrics.get("event_types"),
            "top_events": top[:5],
        },
    }


def _upsert_executive(client: Any, cfg: BigQueryConfig, row: dict[str, Any]) -> dict[str, Any]:
    return _upsert_executive_batch(client, cfg, [row])


def _upsert_executive_batch(
    client: Any, cfg: BigQueryConfig, rows: list[dict[str, Any]]
) -> dict[str, Any]:
    from google.cloud import bigquery

    if not rows:
        return {"status": "empty"}
    table_id = f"{cfg.project}.marts.executive"
    staging = f"{table_id}_staging"
    dest = client.get_table(table_id)
    client.load_table_from_json(
        rows,
        staging,
        job_config=bigquery.LoadJobConfig(
            schema=dest.schema,
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
            source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        ),
    ).result()
    client.query(
        f"""
        MERGE `{table_id}` T
        USING `{staging}` S
        ON T.product = S.product
           AND T.period_date = S.period_date
           AND IFNULL(T.cadence, 'daily') = IFNULL(S.cadence, 'daily')
        WHEN MATCHED THEN UPDATE SET
          metrics_json = S.metrics_json,
          updated_at = S.updated_at
        WHEN NOT MATCHED THEN INSERT (period_date, product, cadence, metrics_json, updated_at)
        VALUES (S.period_date, S.product, S.cadence, S.metrics_json, S.updated_at)
        """,
        location=cfg.location,
    ).result()
    return {"status": "ok", "rows_upserted": len(rows)}


def _maybe_email(metrics: dict[str, Any]) -> dict[str, Any]:
    """Optional: send portfolio summary via existing email notifier env."""
    import os

    to = os.getenv("DIGEST_EMAIL_TO", "").strip()
    if not to or not os.getenv("SMTP_PASSWORD", "").strip():
        return {"status": "skipped", "reason": "email_env_unset"}
    try:
        body = (
            "Portfolio executive summary\n\n"
            + (metrics.get("executive_summary") or "")
            + "\n\nDirection:\n"
            + (metrics.get("direction") or "")
            + "\n\nPriorities:\n"
            + "\n".join(
                f"{p.get('rank')}. [{p.get('product')}] {p.get('action')} — {p.get('rationale')}"
                for p in (metrics.get("priorities") or [])
            )
            + "\n\nRisks:\n"
            + "\n".join(f"- {r}" for r in (metrics.get("risks") or []))
        )
        # Minimal send via SMTP
        import smtplib
        from email.mime.text import MIMEText

        msg = MIMEText(body)
        msg["Subject"] = "Insights portfolio executive summary"
        msg["From"] = os.getenv("SMTP_FROM") or os.getenv("SMTP_USER")
        msg["To"] = to
        with smtplib.SMTP(os.getenv("SMTP_HOST", "smtp.gmail.com"), int(os.getenv("SMTP_PORT", "587"))) as s:
            s.starttls()
            s.login(os.getenv("SMTP_USER", ""), os.getenv("SMTP_PASSWORD", ""))
            s.send_message(msg)
        return {"status": "sent", "to": to}
    except Exception as exc:
        return {"status": "error", "error": str(exc)[:200]}
