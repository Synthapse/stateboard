"""BigQuery config for Insights Digests (cognispace marts)."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class BigQueryConfig:
    project: str
    snapshot_table: str
    strategy_table: str
    location: str

    @classmethod
    def from_env(cls) -> BigQueryConfig:
        project = os.getenv("BQ_PROJECT", "cognispace").strip()
        dataset = os.getenv("BQ_DATASET_INSIGHTS", "marts_insights").strip()
        snapshot = os.getenv("BQ_SNAPSHOT_TABLE", "snapshot_daily").strip()
        strategy = os.getenv("BQ_STRATEGY_TABLE", "product_strategy").strip()
        location = os.getenv("BQ_LOCATION", "EU").strip()
        return cls(
            project=project,
            snapshot_table=f"{project}.{dataset}.{snapshot}",
            strategy_table=f"{project}.{dataset}.{strategy}",
            location=location,
        )
