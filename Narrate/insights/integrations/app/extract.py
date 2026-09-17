"""Run all app extracts → raw_app + dim_user / dim_account."""

from __future__ import annotations

from typing import Any

from insights.domain.models import Product
from insights.integrations.app.lindle_neo4j import extract_lindle
from insights.integrations.app.sql_extract import extract_kih, extract_yca


def app_extract(product: Product | str | None = None) -> list[dict[str, Any]]:
    """Fail-open per product. product=None → all three."""
    out: list[dict[str, Any]] = []
    targets = [Product(product)] if product else list(Product)
    for p in targets:
        if p is Product.KIH:
            out.extend(extract_kih())
        elif p is Product.YCA:
            out.extend(extract_yca())
        elif p is Product.LINDLE:
            out.extend(extract_lindle())
    return out
