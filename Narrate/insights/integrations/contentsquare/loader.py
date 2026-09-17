"""Contentsquare — UX SoT. Registry + optional API friction signal for Digests."""

from __future__ import annotations

import os
from dataclasses import dataclass

import requests

from insights.domain.models import Product
from insights.integrations.products import get_sources


@dataclass(frozen=True)
class ContentsquareSignal:
    """Lightweight UX signal for Snapshot reliability_flags / Digest details."""

    project_id: str | None
    status: str  # ok | missing_id | no_api_key | error
    note: str
    source: str = "contentsquare"


class ContentsquareLoader:
    """
    Contentsquare is the UX system of truth (plan).
    UI: confirm project id in CS Console; create API credentials for ETL.
    Full session warehouse is out of scope — Digests only need a friction skim.
    """

    def load(self, product: Product | str) -> ContentsquareSignal:
        product = Product(product)
        sources = get_sources(product)
        if sources.ux_primary != "contentsquare":
            return ContentsquareSignal(
                project_id=None,
                status="skipped",
                note="",
            )
        cs_id = (
            os.getenv(f"CONTENTSQUARE_{product.value.upper()}_PROJECT_ID", "").strip()
            or sources.contentsquare_id
        )
        if not cs_id:
            return ContentsquareSignal(
                project_id=None,
                status="missing_id",
                note=f"Set Contentsquare project id for {product.value} (SoT UX).",
            )

        api_key = (
            os.getenv(f"CONTENTSQUARE_{product.value.upper()}_API_KEY", "").strip()
            or os.getenv("CONTENTSQUARE_API_KEY", "").strip()
        )
        if not api_key:
            return ContentsquareSignal(
                project_id=cs_id,
                status="no_api_key",
                note=f"CS project {cs_id} registered — add CONTENTSQUARE_API_KEY to pull friction metrics.",
            )

        # Optional live check — endpoint varies by CS API version; fail-open with registry proof
        base = os.getenv("CONTENTSQUARE_API_BASE", "https://api.contentsquare.com").rstrip("/")
        try:
            resp = requests.get(
                f"{base}/v1/projects/{cs_id}",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=30,
            )
            if resp.status_code < 400:
                return ContentsquareSignal(
                    project_id=cs_id,
                    status="ok",
                    note=f"Contentsquare project {cs_id} reachable.",
                )
            return ContentsquareSignal(
                project_id=cs_id,
                status="error",
                note=f"Contentsquare API HTTP {resp.status_code} for {cs_id}.",
            )
        except Exception as exc:
            return ContentsquareSignal(
                project_id=cs_id,
                status="error",
                note=f"Contentsquare API error: {exc}",
            )
