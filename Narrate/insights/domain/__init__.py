"""Domain package — Digests models re-export shared GTM types."""

from document.MultiAgent.gtm_structure import GTMRequest, GTMSection, GTMStrategy
from insights.domain.models import (
    Cadence,
    DeliveryChannel,
    Enrichment,
    InsightsSnapshot,
    MetricDetail,
    Product,
    ProductStrategyHold,
)

__all__ = [
    "Cadence",
    "DeliveryChannel",
    "Enrichment",
    "GTMRequest",
    "GTMSection",
    "GTMStrategy",
    "InsightsSnapshot",
    "MetricDetail",
    "Product",
    "ProductStrategyHold",
]
