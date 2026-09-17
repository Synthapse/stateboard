"""Gemini StrategyRefresher — validates via GTMStrategy; fills subsections; fail-open."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from document.MultiAgent.gtm_structure import GTMStrategy
from insights.application.normalize_gtm import (
    SECTION_SUBSECTION_HINTS,
    ensure_hold_subsections,
    normalize_section,
)
from insights.application.refresh_strategy import SnapshotStrategyRefresher
from insights.domain.models import Enrichment, InsightsSnapshot, ProductStrategyHold
from insights.infrastructure.gemini_client import gemini_configured, generate_json

_SYSTEM = (
    "You are a product strategist. Prior GTMStrategy + InsightsSnapshot are given. "
    "Update every top-level section. Use ONLY Snapshot numbers — never invent "
    "sessions, users, or costs. "
    "executive_summary MUST be a plain string (not an object) and MUST NOT copy "
    "enrichment.executive_skim verbatim — write a distinct GTM-oriented summary. "
    "Each other section MUST be an object: "
    '{"title": str, "content": str (short intro ≤40 words), '
    '"subsections": [{"title": str, "content": str (≤60 words)}] }. '
    "Fill subsections using the provided hints (2–4 items). "
    "Do not leave subsections null/empty when hints exist. "
    "Output full GTMStrategy JSON only."
)

_SECTION_KEYS = tuple(
    name for name in GTMStrategy.model_fields if name not in ("title", "executive_summary")
)


class GeminiStrategyRefresher:
    def __init__(self) -> None:
        self._fallback = SnapshotStrategyRefresher()

    def refresh(
        self,
        hold: ProductStrategyHold,
        snapshot: InsightsSnapshot,
        enrichment: Enrichment | None = None,
    ) -> ProductStrategyHold:
        if not gemini_configured():
            print("GEMINI_API_KEY unset — template strategy refresh")
            return self._fallback.refresh(hold, snapshot, enrichment)

        try:
            payload = {
                "prior_gtm": hold.to_gtm_strategy().model_dump(mode="json"),
                "gtm_request": hold.to_gtm_request().model_dump(mode="json"),
                "snapshot": snapshot.model_dump(mode="json"),
                "enrichment": enrichment.model_dump(mode="json") if enrichment else None,
                "subsection_hints": SECTION_SUBSECTION_HINTS,
            }
            raw = generate_json(
                prompt="Refresh the GTMStrategy with nested subsections:\n"
                + json.dumps(payload, default=str),
                system=_SYSTEM,
            )
            if not raw.get("title"):
                raw["title"] = hold.title
            raw["executive_summary"] = _as_summary_text(
                raw.get("executive_summary"), fallback=hold.executive_summary
            )

            for key in _SECTION_KEYS:
                prior = getattr(hold, key)
                raw[key] = normalize_section(raw.get(key), fallback=prior).model_dump()

            gtm = GTMStrategy.model_validate(raw)
            hold = ProductStrategyHold.from_gtm(
                gtm,
                product=hold.product,
                cadence=hold.cadence,
                period_date=snapshot.period_date,
                request=hold.to_gtm_request(),
                refreshed_by="gemini_strategy_refresher",
                updated_at=datetime.now(timezone.utc),
                schema_version=hold.schema_version,
            )
            return ensure_hold_subsections(hold)
        except Exception as exc:
            print(f"Gemini strategy refresh failed ({exc}); template refresh")
            return self._fallback.refresh(hold, snapshot, enrichment)


def _as_summary_text(raw: object, *, fallback: str) -> str:
    """Gemini sometimes returns executive_summary as a section object — coerce to str."""
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    if isinstance(raw, dict):
        content = raw.get("content")
        if isinstance(content, str) and content.strip():
            return content.strip()
        title = raw.get("title")
        if isinstance(title, str) and title.strip():
            return title.strip()
    return fallback or ""
