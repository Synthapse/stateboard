"""Domain models for Insights Digests — reuses MultiAgent GTM structures."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from document.MultiAgent.gtm_structure import GTMRequest, GTMSection, GTMStrategy

# Re-export so Digests callers import from domain, not legacy paths only
__all_gtm__ = ("GTMSection", "GTMStrategy", "GTMRequest")


class Product(str, Enum):
    KIH = "kih"
    LINDLE = "lindle"
    YCA = "yca"


class Cadence(str, Enum):
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class DeliveryChannel(str, Enum):
    EMAIL = "email"
    SLACK = "slack"


class InsightsSnapshot(BaseModel):
    schema_version: int = 1
    product: Product
    period_date: date
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    sessions: Optional[int] = None
    sessions_delta_pct: Optional[float] = None
    users: Optional[int] = None
    cloud_cost_usd: Optional[float] = None
    cloud_cost_delta_pct: Optional[float] = None
    ai_cost_usd: Optional[float] = None
    reliability_flags: list[str] = Field(default_factory=list)
    watch_bullets: list[str] = Field(default_factory=list)

    @field_validator("watch_bullets")
    @classmethod
    def at_most_three_watch(cls, v: list[str]) -> list[str]:
        return v[:3]

    @field_validator("reliability_flags")
    @classmethod
    def at_most_three_flags(cls, v: list[str]) -> list[str]:
        return v[:3]


class ProductStrategyHold(GTMStrategy):
    """
    Living per-product strategy hold = GTMStrategy (+ Digest metadata + GTMRequest seeds).
    Same section model as document/MultiAgent/gtm_structure.py — single source of truth.
    """

    schema_version: int = 1
    product: Product
    cadence: Cadence = Cadence.WEEKLY
    period_date: date
    # GTMRequest seeds (kept on the hold so Digests / gtm_gen share one blob)
    product_description: str = ""
    target_market: str = ""
    budget_range: Optional[str] = None
    timeline_constraints: Optional[str] = None
    updated_at: Optional[datetime] = None
    refreshed_by: str = "digest_run"

    def to_gtm_strategy(self) -> GTMStrategy:
        data = {name: getattr(self, name) for name in GTMStrategy.model_fields}
        return GTMStrategy.model_validate(data)

    def to_gtm_request(self) -> GTMRequest:
        return GTMRequest(
            title=self.title,
            product_description=self.product_description or self.title,
            target_market=self.target_market or self.product.value,
            budget_range=self.budget_range,
            timeline_constraints=self.timeline_constraints,
        )

    @classmethod
    def from_gtm(
        cls,
        gtm: GTMStrategy,
        *,
        product: Product,
        cadence: Cadence,
        period_date: date,
        request: GTMRequest | None = None,
        refreshed_by: str = "digest_run",
        updated_at: datetime | None = None,
        schema_version: int = 1,
    ) -> ProductStrategyHold:
        payload = gtm.model_dump()
        payload.update(
            {
                "product": product,
                "cadence": cadence,
                "period_date": period_date,
                "refreshed_by": refreshed_by,
                "updated_at": updated_at,
                "schema_version": schema_version,
            }
        )
        if request:
            payload.update(
                {
                    "product_description": request.product_description,
                    "target_market": request.target_market,
                    "budget_range": request.budget_range,
                    "timeline_constraints": request.timeline_constraints,
                }
            )
        return cls.model_validate(payload)


class MetricDetail(BaseModel):
    """One BQ-backed fact shown in Digest enrichment details."""

    label: str
    value: str
    source: str = "marts_insights.snapshot_daily"


class Enrichment(BaseModel):
    """Narrative layer + mandatory BQ metric details (never invent numbers)."""

    insights: list[str] = Field(default_factory=list)
    watch_bullets: list[str] = Field(default_factory=list)
    executive_skim: str = ""
    details: list[MetricDetail] = Field(default_factory=list)

    @field_validator("insights", mode="before")
    @classmethod
    def coerce_insights(cls, v: object) -> list[str]:
        if not v:
            return []
        if not isinstance(v, list):
            return []
        out: list[str] = []
        for item in v:
            if isinstance(item, str) and item.strip():
                out.append(item.strip())
            elif isinstance(item, dict):
                obs = str(item.get("observation") or item.get("insight") or "").strip()
                impl = str(item.get("implication") or item.get("so_what") or "").strip()
                act = str(
                    item.get("action")
                    or item.get("suggested_action")
                    or item.get("next_step")
                    or ""
                ).strip()
                parts = [p for p in (obs, impl, act) if p]
                if parts:
                    out.append(" — ".join(parts))
        return out[:3]

    @field_validator("watch_bullets", mode="before")
    @classmethod
    def coerce_watch(cls, v: object) -> list[str]:
        if not v:
            return []
        if not isinstance(v, list):
            return []
        out: list[str] = []
        for item in v:
            if isinstance(item, str) and item.strip():
                out.append(item.strip())
            elif isinstance(item, dict):
                text = (
                    item.get("watch")
                    or item.get("bullet")
                    or item.get("text")
                    or item.get("observation")
                )
                if text:
                    out.append(str(text).strip())
        return out[:3]
