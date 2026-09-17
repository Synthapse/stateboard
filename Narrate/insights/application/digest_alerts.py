"""Daily red-flag alerts from existing marts (no new collectors)."""

from __future__ import annotations

import os
from typing import Any

from insights.domain.models import Product
from insights.integrations.bigquery.client import get_bigquery_client
from insights.integrations.bigquery.config import BigQueryConfig


def collect_red_flags() -> list[dict[str, Any]]:
    """
    Scan latest marts.reliability + marts.ai per product.
    Returns list of {product, kind, message}.
    """
    cfg = BigQueryConfig.from_env()
    client = get_bigquery_client(cfg.project)
    flags: list[dict[str, Any]] = []

    for product in Product:
        p = product.value
        try:
            rel = _latest_mart_metrics(client, cfg, "reliability", p)
            if rel:
                down = rel.get("services_down") or 0
                failing = rel.get("failing") or []
                if down or failing:
                    names = [
                        (f.get("service") or f.get("name") or str(f))
                        if isinstance(f, dict)
                        else str(f)
                        for f in failing[:3]
                    ]
                    msg = f"{p}: {down} service(s) down"
                    if names:
                        msg += " — " + ", ".join(names)
                    flags.append({"product": p, "kind": "reliability", "message": msg})
        except Exception as exc:
            print(f"alert reliability {p}: {exc}")

        try:
            ai = _latest_mart_metrics(client, cfg, "ai", p)
            if ai:
                traces = ai.get("trace_count") or 0
                cost = ai.get("total_cost_usd")
                if traces > 0 and (cost is None or float(cost) == 0):
                    flags.append(
                        {
                            "product": p,
                            "kind": "ai_cost_gap",
                            "message": (
                                f"{p}: {int(traces)} Langfuse traces but AI $0 "
                                "(enable model pricing)"
                            ),
                        }
                    )
        except Exception as exc:
            print(f"alert ai {p}: {exc}")

    return flags


def send_daily_alerts(*, send_email: bool = True) -> dict[str, Any]:
    """
    If red flags exist and SMTP configured, email DIGEST_EMAIL_TO.
    Set DIGEST_DAILY_ALERTS=0 to skip.
    """
    if os.getenv("DIGEST_DAILY_ALERTS", "1").strip() == "0":
        return {"status": "skipped", "reason": "DIGEST_DAILY_ALERTS=0"}

    flags = collect_red_flags()
    if not flags:
        return {"status": "ok", "flags": 0, "sent": False}

    body = "Insights daily alerts\n\n" + "\n".join(f"• {f['message']}" for f in flags)
    subject = f"[Insights] {len(flags)} daily alert(s)"

    result: dict[str, Any] = {
        "status": "ok",
        "flags": len(flags),
        "items": flags,
        "sent": False,
    }
    if not send_email:
        result["body"] = body
        return result

    to = os.getenv("DIGEST_EMAIL_TO", "").strip()
    if not to or not os.getenv("SMTP_PASSWORD", "").strip():
        result["status"] = "flags_only"
        result["reason"] = "email_env_unset"
        result["body"] = body
        return result

    try:
        import smtplib
        from email.mime.text import MIMEText

        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = os.getenv("SMTP_FROM") or os.getenv("SMTP_USER")
        msg["To"] = to
        with smtplib.SMTP(
            os.getenv("SMTP_HOST", "smtp.gmail.com"),
            int(os.getenv("SMTP_PORT", "587")),
        ) as s:
            s.starttls()
            s.login(os.getenv("SMTP_USER", ""), os.getenv("SMTP_PASSWORD", ""))
            s.send_message(msg)
        result["sent"] = True
        result["to"] = to
    except Exception as exc:
        result["status"] = "send_failed"
        result["error"] = str(exc)[:200]
        result["body"] = body
    return result


def _latest_mart_metrics(
    client: Any,
    cfg: BigQueryConfig,
    mart: str,
    product: str,
) -> dict[str, Any] | None:
    import json

    sql = f"""
    SELECT metrics_json
    FROM `{cfg.project}.marts.{mart}`
    WHERE product = '{product}'
    ORDER BY period_date DESC
    LIMIT 1
    """
    rows = list(client.query(sql, location=cfg.location).result())
    if not rows:
        return None
    mj = rows[0]["metrics_json"]
    if hasattr(mj, "items"):
        return dict(mj)
    if isinstance(mj, str):
        return json.loads(mj)
    return mj if isinstance(mj, dict) else None
