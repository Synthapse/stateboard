"""Langfuse API → aggregates for Digests (live) + shared helpers for daily ETL.

Uses Metrics API v2: GET /api/public/v2/metrics?query=…
https://langfuse.com/docs/metrics/features/metrics-api
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

import requests

from insights.domain.models import Product
from insights.integrations.products import LANGFUSE_HOST_DEFAULT


@dataclass(frozen=True)
class LangfuseMetrics:
    total_cost_usd: float | None
    trace_count: int | None  # observation count (v2 has no traces view)
    source: str = "langfuse_api"


def _keys_for(product: Product) -> tuple[str, str]:
    """Per-product keys, else shared LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY."""
    prefix = f"LANGFUSE_{product.value.upper()}_"
    pub = os.getenv(f"{prefix}PUBLIC_KEY", "").strip() or os.getenv("LANGFUSE_PUBLIC_KEY", "").strip()
    sec = os.getenv(f"{prefix}SECRET_KEY", "").strip() or os.getenv("LANGFUSE_SECRET_KEY", "").strip()
    return pub, sec


class LangfuseMetricsLoader:
    """
    Pull LLM cost / volume from Langfuse Metrics API v2 (EU cloud).
    UI: create API keys in Langfuse project settings (see docs/ui-setup-load-paths.md §3).
    """

    def __init__(self, host: str | None = None) -> None:
        self.host = (host or os.getenv("LANGFUSE_HOST", LANGFUSE_HOST_DEFAULT)).rstrip("/")

    def load(self, product: Product | str, *, lookback_days: int = 7) -> LangfuseMetrics:
        product = Product(product)
        pub, sec = _keys_for(product)
        if not pub or not sec:
            print(f"Langfuse keys unset for {product.value} — skipping LLM metrics")
            return LangfuseMetrics(total_cost_usd=None, trace_count=None)

        end = date.today()
        start = end - timedelta(days=lookback_days)
        try:
            return self.fetch_range(pub, sec, start, end)
        except Exception as exc:
            print(f"Langfuse load failed for {product.value}: {exc}")
            return LangfuseMetrics(total_cost_usd=None, trace_count=None)

    def fetch_range(self, pub: str, sec: str, start: date, end: date) -> LangfuseMetrics:
        """Inclusive calendar days [start, end] → cost + observation count."""
        data = self._metrics_v2(
            pub,
            sec,
            {
                "view": "observations",
                "metrics": [
                    {"measure": "totalCost", "aggregation": "sum"},
                    {"measure": "count", "aggregation": "count"},
                ],
                "filters": [],
                "fromTimestamp": f"{start.isoformat()}T00:00:00Z",
                # exclusive end: day after `end`
                "toTimestamp": f"{(end + timedelta(days=1)).isoformat()}T00:00:00Z",
            },
        )
        cost = _field_sum(data, "sum_totalCost", "totalCost")
        count = _field_sum(data, "count_count", "count")
        return LangfuseMetrics(
            total_cost_usd=cost,
            trace_count=int(count) if count is not None else None,
        )

    def _metric_sum(
        self,
        pub: str,
        sec: str,
        measure: str,
        start: date,
        end: date,
        *,
        view: str = "observations",
    ) -> float | None:
        """Legacy helper used by daily ETL — prefer fetch_range for both metrics."""
        _ = view  # v2: traces view removed; always observations
        agg = "count" if measure == "count" else "sum"
        data = self._metrics_v2(
            pub,
            sec,
            {
                "view": "observations",
                "metrics": [{"measure": measure, "aggregation": agg}],
                "filters": [],
                "fromTimestamp": f"{start.isoformat()}T00:00:00Z",
                "toTimestamp": f"{(end + timedelta(days=1)).isoformat()}T00:00:00Z",
            },
        )
        if measure == "totalCost":
            return _field_sum(data, "sum_totalCost", "totalCost")
        if measure == "count":
            return _field_sum(data, "count_count", "count")
        return _extract_metric_value(data)

    def _metrics_v2(self, pub: str, sec: str, query: dict[str, Any]) -> Any:
        url = f"{self.host}/api/public/v2/metrics"
        resp = requests.get(
            url,
            params={"query": json.dumps(query)},
            auth=(pub, sec),
            timeout=60,
        )
        if resp.status_code >= 400:
            snippet = (resp.text or "")[:300]
            print(f"Langfuse metrics v2 HTTP {resp.status_code}: {snippet}")
            resp.raise_for_status()
        return resp.json()


def _field_sum(data: Any, *keys: str) -> float | None:
    rows = data.get("data") if isinstance(data, dict) else data
    if not isinstance(rows, list):
        return _extract_metric_value(data)
    total = 0.0
    found = False
    for row in rows:
        if not isinstance(row, dict):
            continue
        for key in keys:
            if key in row and row[key] is not None:
                try:
                    total += float(row[key])
                    found = True
                    break
                except (TypeError, ValueError):
                    pass
    return total if found else None


def _extract_metric_value(data: Any) -> float | None:
    if isinstance(data, (int, float)):
        return float(data)
    if isinstance(data, dict):
        for key in ("sum_totalCost", "count_count", "data", "result", "metrics", "rows"):
            if key in data:
                val = _extract_metric_value(data[key]) if key in ("data", "result", "metrics", "rows") else data[key]
                if key in ("sum_totalCost", "count_count") and data[key] is not None:
                    try:
                        return float(data[key])
                    except (TypeError, ValueError):
                        pass
                if val is not None and key in ("data", "result", "metrics", "rows"):
                    return val
        for key in ("sum", "value", "totalCost", "total", "count"):
            if key in data and data[key] is not None:
                try:
                    return float(data[key])
                except (TypeError, ValueError):
                    pass
    if isinstance(data, list) and data:
        return _extract_metric_value(data[0])
    return None
