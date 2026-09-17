"""Microsoft Clarity Data Export API → Digests signal + shared fetch for ETL.

API: GET https://www.clarity.ms/export-data/api/v1/project-live-insights
Auth: Bearer token (project-scoped). numOfDays ∈ {1,2,3}. Max 10 req/project/day.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import requests

from insights.domain.models import Product
from insights.integrations.products import get_sources

CLARITY_API_URL_DEFAULT = "https://www.clarity.ms/export-data/api/v1/project-live-insights"


@dataclass(frozen=True)
class ClaritySignal:
    project_id: str | None
    status: str  # ok | none | no_token | error
    note: str
    payload: Any = None
    source: str = "clarity"


def clarity_project_id(product: Product) -> str | None:
    sources = get_sources(product)
    return (
        os.getenv(f"CLARITY_{product.value.upper()}_PROJECT_ID", "").strip()
        or sources.clarity_project_id
        or None
    )


def clarity_token(product: Product) -> str:
    """Per-product API_KEY / API_TOKEN, else shared CLARITY_API_TOKEN / CLARITY_API_KEY."""
    prefix = f"CLARITY_{product.value.upper()}_"
    return (
        os.getenv(f"{prefix}API_KEY", "").strip()
        or os.getenv(f"{prefix}API_TOKEN", "").strip()
        or os.getenv("CLARITY_API_TOKEN", "").strip()
        or os.getenv("CLARITY_API_KEY", "").strip()
    )


class ClarityLoader:
    """
    Clarity UX for Lindle/YCA (KIH uses Contentsquare).
    UI: Clarity → Settings → Data Export → Generate API token.
    """

    def load(self, product: Product | str, *, num_of_days: int = 1) -> ClaritySignal:
        product = Product(product)
        clarity_id = clarity_project_id(product)
        if not clarity_id:
            return ClaritySignal(
                project_id=None,
                status="none",
                note=f"No Clarity project for {product.value}.",
            )

        token = clarity_token(product)
        if not token:
            return ClaritySignal(
                project_id=clarity_id,
                status="no_token",
                note=f"Clarity {clarity_id} registered — add CLARITY_{product.value.upper()}_API_KEY.",
            )

        try:
            payload = self.fetch(token, num_of_days=num_of_days, project_id=clarity_id)
            return ClaritySignal(
                project_id=clarity_id,
                status="ok",
                note=f"Clarity {clarity_id} export ok.",
                payload=payload,
            )
        except Exception as exc:
            return ClaritySignal(
                project_id=clarity_id,
                status="error",
                note=f"Clarity API error: {exc}",
            )

    def fetch(
        self,
        token: str,
        *,
        num_of_days: int = 1,
        project_id: str | None = None,
    ) -> Any:
        """
        Fetch live insights. Token is project-scoped; projectId is optional query param.
        num_of_days must be 1, 2, or 3.
        Bypass env HTTP(S)_PROXY — Clarity often fails behind corporate proxies (403 Tunnel).
        """
        days = max(1, min(int(num_of_days), 3))
        url = os.getenv("CLARITY_API_URL", CLARITY_API_URL_DEFAULT)
        params: dict[str, str] = {"numOfDays": str(days)}
        if project_id:
            params["projectId"] = project_id
        resp = requests.get(
            url,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            params=params,
            timeout=45,
            proxies={"http": None, "https": None},
        )
        if resp.status_code >= 400:
            snippet = (resp.text or "")[:300]
            raise RuntimeError(f"HTTP {resp.status_code}: {snippet}")
        try:
            return resp.json()
        except Exception:
            return {"raw": resp.text}
