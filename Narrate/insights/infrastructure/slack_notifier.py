"""Slack DigestNotifier — switch via DIGEST_CHANNEL=slack."""

from __future__ import annotations

import os

import requests


class SlackNotifier:
    channel = "slack"

    def __init__(self, webhook_url: str | None = None) -> None:
        self.webhook_url = (webhook_url or os.getenv("SLACK_WEBHOOK_URL", "")).strip()

    def send(
        self,
        subject: str,
        body: str,
        *,
        product: str | None = None,
        cadence: str | None = None,
        period_date: str | None = None,
    ) -> bool:
        _ = (product, cadence, period_date)
        if not self.webhook_url:
            print("SLACK_WEBHOOK_URL unset — skipping Slack send")
            print(f"---\n{subject}\n\n{body}\n---")
            return False

        # Slack Incoming Webhooks: subject folded into text
        text = f"*{subject}*\n{body}"
        resp = requests.post(self.webhook_url, json={"text": text}, timeout=30)
        resp.raise_for_status()
        return True
