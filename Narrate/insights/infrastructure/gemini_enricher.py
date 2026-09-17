"""Gemini DigestEnricher — actionable insights grounded on marts facts; fail-open."""

from __future__ import annotations

import json
from typing import Any

from insights.application.bq_details import snapshot_details
from insights.domain.models import Enrichment, InsightsSnapshot, ProductStrategyHold
from insights.infrastructure.gemini_client import gemini_configured, generate_json

_SYSTEM = (
    "You are a product analyst for a SaaS product Digest email. "
    "The `details` array and `facts` object are BigQuery source-of-truth "
    "(snapshot_daily + marts.product/customer/ai/cost/reliability + optional core costs). "
    "Use ONLY those values — never invent numbers, Clarity metrics, or revenue. "
    "If a signal is missing, say so briefly; do not fabricate. "
    "Do NOT restate the KPI block (sessions/users/cloud/AI) as your main content. "
    "Prefer CROSS-LENS insights (growth vs cost, AI traces vs AI $, events vs reliability). "
    "Output JSON only with keys: "
    '{"insights": ["…"] (max 3 strings; each = observation + implication + suggested action, '
    "cite a detail label/value — plain strings only, not objects), "
    '"watch_bullets": ["…"] (max 3, actionable, cite a detail), '
    '"executive_skim": "…" (~60 words; omit if insights already cover the story)}. '
    "Do not output a details array — the server attaches BQ details."
)


class GeminiEnricher:
    def enrich(
        self,
        snapshot: InsightsSnapshot,
        strategy: ProductStrategyHold | None = None,
        facts: dict[str, Any] | None = None,
    ) -> Enrichment:
        details = snapshot_details(snapshot, facts)
        if not gemini_configured():
            print("GEMINI_API_KEY unset — BQ details only (no GenAI skim)")
            return Enrichment(details=details)

        try:
            payload = {
                "details": [d.model_dump() for d in details],
                "facts": facts or {},
                "snapshot": snapshot.model_dump(mode="json"),
                "strategy_title": strategy.title if strategy else None,
                "strategy_executive_summary": strategy.executive_summary if strategy else None,
            }
            raw = generate_json(
                prompt="Write Digest insights from warehouse facts:\n"
                + json.dumps(payload, default=str),
                system=_SYSTEM,
            )
            enrichment = Enrichment.model_validate(raw)
            enrichment.details = details  # always BQ — ignore any model-invented details
            return enrichment
        except Exception as exc:
            print(f"Gemini enrich failed ({exc}); BQ details only")
            return Enrichment(details=details)
