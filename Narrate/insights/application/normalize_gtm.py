"""GTM section helpers — normalize trees + ensure subsections from hints."""

from __future__ import annotations

from typing import Any

from document.MultiAgent.gtm_structure import GTMSection, GTMStrategy
from insights.domain.models import ProductStrategyHold

# Stable subsection titles per GTMStrategy field (Gemini + template)
SECTION_SUBSECTION_HINTS: dict[str, list[str]] = {
    "market_analysis": [
        "Market size & growth",
        "Trends",
        "Competitive landscape",
        "Barriers & opportunities",
    ],
    "target_segments": [
        "Primary segments",
        "Needs & jobs-to-be-done",
        "Prioritization",
    ],
    "positioning_strategy": [
        "Positioning statement",
        "Differentiation",
        "Messaging pillars",
    ],
    "product_strategy": [
        "Near-term bets",
        "Roadmap themes",
        "Success metrics",
    ],
    "pricing_strategy": [
        "Packaging",
        "Unit economics signals",
        "Experiments",
    ],
    "distribution_strategy": [
        "Primary channels",
        "Partners",
        "Inbox / digest motion",
    ],
    "marketing_plan": [
        "This cadence themes",
        "Channels",
        "Measurement",
    ],
    "sales_strategy": [
        "Motion",
        "Pipeline focus",
    ],
    "customer_success": [
        "Health signals",
        "Interventions",
    ],
    "timeline_milestones": [
        "This cadence",
        "Next 30–90 days",
    ],
    "budget_forecast": [
        "Cloud & AI spend",
        "Watch thresholds",
    ],
    "risk_mitigation": [
        "Active flags",
        "Mitigations",
        "Owners / next check",
    ],
}

_SECTION_KEYS = tuple(
    name for name in GTMStrategy.model_fields if name not in ("title", "executive_summary")
)


def normalize_section(raw: Any, *, fallback: GTMSection | None = None) -> GTMSection:
    """Coerce dict/model output into GTMSection with cleaned subsections."""
    if isinstance(raw, GTMSection):
        return _clean(raw)

    if not isinstance(raw, dict):
        return _clean(fallback) if fallback else GTMSection(title="Section", content="")

    title = str(raw.get("title") or (fallback.title if fallback else "Section"))
    content = raw.get("content", "")
    subs_raw = raw.get("subsections")

    if isinstance(content, list) and not subs_raw:
        subs_raw, content = content, ""
    if not isinstance(content, str):
        content = "" if content is None else str(content)

    subsections: list[GTMSection] = []
    if isinstance(subs_raw, list):
        subsections = [normalize_section(item) for item in subs_raw[:8]]
    elif fallback and fallback.subsections:
        subsections = [_clean(s) for s in fallback.subsections[:8]]

    return GTMSection(
        title=title,
        content=content.strip(),
        subsections=subsections or None,
    )


def _clean(section: GTMSection) -> GTMSection:
    if not section.subsections:
        return section
    return GTMSection(
        title=section.title,
        content=section.content,
        subsections=[normalize_section(s) for s in section.subsections[:8]],
    )


def ensure_section_subsections(section: GTMSection, field: str) -> GTMSection:
    """If subsections missing, seed from SECTION_SUBSECTION_HINTS + parent content."""
    section = normalize_section(section)
    hints = SECTION_SUBSECTION_HINTS.get(field) or []
    if section.subsections or not hints:
        return section

    intro = section.content.strip() or f"{section.title} — to refine next cadence."
    subs = [
        GTMSection(
            title=hint,
            content=intro if i == 0 else f"See parent: {section.title}. Refine with live Snapshot.",
        )
        for i, hint in enumerate(hints)
    ]
    return GTMSection(title=section.title, content=intro, subsections=subs)


def ensure_hold_subsections(hold: ProductStrategyHold) -> ProductStrategyHold:
    """Guarantee every GTM section on the hold has subsections."""
    for field in _SECTION_KEYS:
        setattr(hold, field, ensure_section_subsections(getattr(hold, field), field))
    return hold
