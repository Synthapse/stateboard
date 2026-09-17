"""HTTP / CLI entrypoints — Digests + Snapshot build + Langfuse ETL."""

from __future__ import annotations

import json
import os
from typing import Any

from dotenv import load_dotenv

from insights.application.digest_run import DigestRunUseCase
from insights.domain.models import Cadence, Product
from insights.infrastructure.wiring import (
    build_enricher,
    build_notifier,
    build_snapshot_repo,
    build_strategy_refresher,
    build_strategy_repo,
)

load_dotenv()


def digest_run(
    product: Product | str = Product.KIH,
    cadence: Cadence | str = Cadence.WEEKLY,
) -> dict[str, Any]:
    use_case = DigestRunUseCase(
        snapshots=build_snapshot_repo(),
        strategies=build_strategy_repo(),
        notifier=build_notifier(),
        enricher=build_enricher(),
        refresher=build_strategy_refresher(),
    )
    return use_case.execute(product, cadence)


def digest_run_all(cadence: Cadence | str = Cadence.WEEKLY) -> list[dict[str, Any]]:
    """Run Digest for every Product (Scheduler can call this once per cadence)."""
    return [digest_run(product, cadence) for product in Product]


def build_snapshots(
    product: Product | str | None = None,
    *,
    lookback_days: int = 7,
) -> list[dict[str, Any]]:
    """
    Load path job: GA4 + Billing → marts_insights.snapshot_daily.
    Requires DIGEST_USE_FIXTURE=0 and Console GA4/Billing links (see docs/ui-setup-load-paths.md).
    """
    from insights.integrations.bigquery.snapshot_builder import BigQuerySnapshotBuilder

    builder = BigQuerySnapshotBuilder(lookback_days=lookback_days)
    snaps = [builder.build_one(product)] if product else builder.build_all()
    return [
        {
            "product": s.product.value,
            "period_date": str(s.period_date),
            "sessions": s.sessions,
            "users": s.users,
            "cloud_cost_usd": s.cloud_cost_usd,
            "ai_cost_usd": s.ai_cost_usd,
            "sessions_delta_pct": s.sessions_delta_pct,
            "cloud_cost_delta_pct": s.cloud_cost_delta_pct,
        }
        for s in snaps
    ]


def langfuse_etl(
    product: Product | str | None = None,
    *,
    lookback_days: int = 1,
) -> list[dict[str, Any]]:
    """
    Daily ETL: Langfuse Metrics API → cognispace.raw_langfuse.daily_metrics
    and promote into marts.ai.
    Default: yesterday for all products (or one). Use lookback_days>1 to backfill.
    """
    from insights.integrations.langfuse.daily_etl import LangfuseDailyEtl

    return LangfuseDailyEtl().run(product, lookback_days=lookback_days)


def daily_pipeline(
    product: Product | str | None = None,
    *,
    lookback_days: int = 1,
    snapshot_lookback_days: int = 7,
) -> dict[str, Any]:
    """
    M5 daily job: Langfuse ETL (+ marts.ai + core LLM) → billing core →
    GA4 core → Clarity ETL → healthchecks → build_snapshots → app_extract →
    executive GenAI layer → daily red-flag alerts (if any).
    Scheduler: action=daily_pipeline&all=1
    """
    from insights.integrations.app.extract import app_extract
    from insights.integrations.bigquery.billing_core import load_billing_core
    from insights.integrations.bigquery.ga4_core import load_ga4_core
    from insights.integrations.bigquery.langfuse_core import load_langfuse_core

    etl = langfuse_etl(product, lookback_days=lookback_days)
    lf_core = load_langfuse_core(lookback_days=max(lookback_days, 30))
    billing = load_billing_core(lookback_days=60)
    ga4 = load_ga4_core(product, lookback_days=max(snapshot_lookback_days, 14))
    clarity = clarity_etl(product)
    health = healthchecks(product)
    snaps = build_snapshots(product, lookback_days=snapshot_lookback_days)
    apps = app_extract(product)
    executive = executive_summary()
    from insights.application.digest_alerts import send_daily_alerts

    alerts = send_daily_alerts(send_email=True)
    return {
        "langfuse_etl": etl,
        "langfuse_core": lf_core,
        "billing_core": billing,
        "ga4_core": ga4,
        "clarity_etl": clarity,
        "healthchecks": health,
        "snapshots": snaps,
        "app_extract": apps,
        "executive": executive,
        "alerts": alerts,
    }


def core_seed() -> dict[str, Any]:
    from insights.integrations.bigquery.core_seed import seed_core_dims

    return seed_core_dims()


def billing_core(*, lookback_days: int = 60) -> dict[str, Any]:
    from insights.integrations.bigquery.billing_core import load_billing_core

    return load_billing_core(lookback_days=lookback_days)


def langfuse_core(*, lookback_days: int = 30) -> dict[str, Any]:
    from insights.integrations.bigquery.langfuse_core import load_langfuse_core

    return load_langfuse_core(lookback_days=lookback_days)


def ga4_core(
    product: Product | str | None = None,
    *,
    lookback_days: int = 14,
) -> dict[str, Any]:
    from insights.integrations.bigquery.ga4_core import load_ga4_core

    return load_ga4_core(product, lookback_days=lookback_days)


def app_extract(product: Product | str | None = None) -> list[dict[str, Any]]:
    from insights.integrations.app.extract import app_extract as _run

    return _run(product)


def healthchecks(product: Product | str | None = None) -> dict[str, Any]:
    from insights.integrations.bigquery.healthchecks import run_healthchecks

    p = product.value if isinstance(product, Product) else product
    return run_healthchecks(p)


def looker_views() -> dict[str, Any]:
    from insights.integrations.bigquery.looker_views import ensure_looker_views

    return ensure_looker_views()


def executive_summary(*, send_email: bool = False) -> dict[str, Any]:
    """Portfolio GenAI layer over finalized marts + snapshots → marts.executive."""
    from insights.application.executive_layer import run_executive_layer

    return run_executive_layer(send_email=send_email)


def clarity_etl(
    product: Product | str | None = None,
    *,
    num_of_days: int = 3,
) -> list[dict[str, Any]]:
    """
    Daily ETL: Clarity Data Export API → cognispace.raw_clarity.daily_insights.
    API only returns last 1–3 days; one call per product (rate limit ~10/day).
    """
    from insights.integrations.clarity.daily_etl import ClarityDailyEtl

    return ClarityDailyEtl().run(product, num_of_days=num_of_days)


def digest_http(request: Any) -> tuple[str, int, dict[str, str]]:
    """
    Gen2 Cloud Functions HTTP entry.
    Query: product, cadence, all=1, lookback_days, num_of_days,
           action=digest|daily_pipeline|build_snapshots|langfuse_etl|clarity_etl
    """
    raw_product: str | None = None
    raw_cadence = Cadence.WEEKLY.value
    run_all = False
    action = "digest"
    lookback_days = 1
    snapshot_lookback_days = 7
    num_of_days = 3
    body: dict[str, Any] = {}

    if request.args:
        raw_product = request.args.get("product") or raw_product
        raw_cadence = request.args.get("cadence", raw_cadence)
        run_all = request.args.get("all", "").lower() in ("1", "true", "yes")
        action = request.args.get("action", action)
        try:
            lookback_days = int(request.args.get("lookback_days", lookback_days))
        except (TypeError, ValueError):
            pass
        try:
            snapshot_lookback_days = int(
                request.args.get("snapshot_lookback_days", snapshot_lookback_days)
            )
        except (TypeError, ValueError):
            pass
        try:
            num_of_days = int(request.args.get("num_of_days", num_of_days))
        except (TypeError, ValueError):
            pass
    try:
        body = request.get_json(silent=True) or {}
        if body.get("product"):
            raw_product = body["product"]
        raw_cadence = body.get("cadence", raw_cadence)
        run_all = bool(body.get("all", run_all))
        action = body.get("action", action)
        lookback_days = int(body.get("lookback_days", lookback_days))
        snapshot_lookback_days = int(
            body.get("snapshot_lookback_days", snapshot_lookback_days)
        )
        num_of_days = int(body.get("num_of_days", num_of_days))
    except Exception:
        pass

    if "DIGEST_USE_FIXTURE" not in os.environ:
        os.environ["DIGEST_USE_FIXTURE"] = "0"

    def _parse_product() -> Product | None:
        if run_all or not raw_product:
            return None
        return Product(raw_product)

    if action == "daily_pipeline":
        try:
            product = _parse_product()
        except ValueError:
            return (
                json.dumps({"error": f"product must be one of {[p.value for p in Product]}"}),
                400,
                {"Content-Type": "application/json"},
            )
        results = daily_pipeline(
            product,
            lookback_days=lookback_days,
            snapshot_lookback_days=snapshot_lookback_days,
        )
        return json.dumps(results), 200, {"Content-Type": "application/json"}

    if action == "core_seed":
        return json.dumps(core_seed()), 200, {"Content-Type": "application/json"}

    if action == "billing_core":
        return (
            json.dumps(billing_core(lookback_days=max(lookback_days, 60))),
            200,
            {"Content-Type": "application/json"},
        )

    if action == "langfuse_core":
        return (
            json.dumps(langfuse_core(lookback_days=max(lookback_days, 30))),
            200,
            {"Content-Type": "application/json"},
        )

    if action == "ga4_core":
        try:
            product = _parse_product()
        except ValueError:
            return (
                json.dumps({"error": f"product must be one of {[p.value for p in Product]}"}),
                400,
                {"Content-Type": "application/json"},
            )
        return (
            json.dumps(ga4_core(product, lookback_days=max(lookback_days, 14))),
            200,
            {"Content-Type": "application/json"},
        )

    if action == "app_extract":
        try:
            product = _parse_product()
        except ValueError:
            return (
                json.dumps({"error": f"product must be one of {[p.value for p in Product]}"}),
                400,
                {"Content-Type": "application/json"},
            )
        return (
            json.dumps({"extract": app_extract(product)}),
            200,
            {"Content-Type": "application/json"},
        )

    if action == "healthchecks":
        try:
            product = _parse_product()
        except ValueError:
            return (
                json.dumps({"error": f"product must be one of {[p.value for p in Product]}"}),
                400,
                {"Content-Type": "application/json"},
            )
        return (
            json.dumps(healthchecks(product)),
            200,
            {"Content-Type": "application/json"},
        )

    if action == "looker_views":
        return json.dumps(looker_views()), 200, {"Content-Type": "application/json"}

    if action == "executive":
        send_email = False
        if request.args:
            send_email = request.args.get("email", "").lower() in ("1", "true", "yes")
        try:
            body = request.get_json(silent=True) or {}
            send_email = bool(body.get("email", send_email))
        except Exception:
            pass
        return (
            json.dumps(executive_summary(send_email=send_email)),
            200,
            {"Content-Type": "application/json"},
        )

    if action == "marts_ai":
        from insights.integrations.langfuse.marts_ai import promote_marts_ai

        try:
            product = _parse_product()
        except ValueError:
            return (
                json.dumps({"error": f"product must be one of {[p.value for p in Product]}"}),
                400,
                {"Content-Type": "application/json"},
            )
        mart = promote_marts_ai(
            product=product.value if product else None,
            lookback_days=max(lookback_days, 7),
        )
        return json.dumps(mart), 200, {"Content-Type": "application/json"}

    if action == "clarity_etl":
        try:
            product = _parse_product()
        except ValueError:
            return (
                json.dumps({"error": f"product must be one of {[p.value for p in Product]}"}),
                400,
                {"Content-Type": "application/json"},
            )
        results = clarity_etl(product, num_of_days=num_of_days)
        return json.dumps({"etl": results}), 200, {"Content-Type": "application/json"}

    if action == "langfuse_etl":
        try:
            product = _parse_product()
        except ValueError:
            return (
                json.dumps({"error": f"product must be one of {[p.value for p in Product]}"}),
                400,
                {"Content-Type": "application/json"},
            )
        results = langfuse_etl(product, lookback_days=lookback_days)
        return json.dumps({"etl": results}), 200, {"Content-Type": "application/json"}

    if action == "build_snapshots":
        try:
            product = _parse_product()
        except ValueError:
            return (
                json.dumps({"error": f"product must be one of {[p.value for p in Product]}"}),
                400,
                {"Content-Type": "application/json"},
            )
        results = build_snapshots(product, lookback_days=snapshot_lookback_days)
        return json.dumps({"built": results}), 200, {"Content-Type": "application/json"}

    try:
        cadence = Cadence(raw_cadence)
    except ValueError:
        return (
            json.dumps({"error": f"cadence must be one of {[c.value for c in Cadence]}"}),
            400,
            {"Content-Type": "application/json"},
        )

    if run_all:
        results = digest_run_all(cadence)
        return json.dumps({"results": results}), 200, {"Content-Type": "application/json"}

    try:
        product = Product(raw_product or Product.KIH.value)
    except ValueError:
        return (
            json.dumps({"error": f"product must be one of {[p.value for p in Product]}"}),
            400,
            {"Content-Type": "application/json"},
        )

    result = digest_run(product, cadence)
    return json.dumps(result), 200, {"Content-Type": "application/json"}
