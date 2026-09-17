"""Email DigestNotifier — per-product audience + log each send to BigQuery."""

from __future__ import annotations

import os
import smtplib
from datetime import date, datetime, timezone
from email.message import EmailMessage
from typing import Any

DEFAULT_TO = "piotrzak77@gmail.com"
TABLE_ID_SUFFIX = "marts_insights.digest_delivery"


def audience_for(product: str | None) -> list[str]:
    """
    DIGEST_EMAIL_TO_<PRODUCT> (comma-separated), else DIGEST_EMAIL_TO, else default.
    Example: DIGEST_EMAIL_TO_LINDLE=a@x.com,b@y.com
    """
    raw = ""
    if product:
        raw = os.getenv(f"DIGEST_EMAIL_TO_{product.upper()}", "").strip()
    if not raw:
        raw = (os.getenv("DIGEST_EMAIL_TO") or DEFAULT_TO).strip()
    return [a.strip() for a in raw.split(",") if a.strip()]


class EmailNotifier:
    channel = "email"

    def __init__(
        self,
        to_addr: str | None = None,
        from_addr: str | None = None,
        host: str | None = None,
        port: int | None = None,
        user: str | None = None,
        password: str | None = None,
    ) -> None:
        # Legacy single default; send() resolves per-product audience
        self._default_to = (to_addr or os.getenv("DIGEST_EMAIL_TO") or DEFAULT_TO).strip()
        self.from_addr = (
            from_addr or os.getenv("SMTP_FROM") or os.getenv("SMTP_USER") or self._default_to
        ).strip()
        self.host = (host or os.getenv("SMTP_HOST", "smtp.gmail.com")).strip()
        self.port = int(port or os.getenv("SMTP_PORT", "587"))
        self.user = (user or os.getenv("SMTP_USER", "")).strip()
        self.password = (password or os.getenv("SMTP_PASSWORD", "")).strip()

    def send(
        self,
        subject: str,
        body: str,
        *,
        product: str | None = None,
        cadence: str | None = None,
        period_date: str | date | None = None,
    ) -> bool:
        recipients = audience_for(product)
        audience = ", ".join(recipients)

        delivered = False
        if not self.user or not self.password:
            print(
                f"SMTP_USER/SMTP_PASSWORD unset — skipping email "
                f"(would send to {audience})"
            )
            print(f"---\nSubject: {subject}\nTo: {audience}\n\n{body}\n---")
        else:
            msg = EmailMessage()
            msg["Subject"] = subject
            msg["From"] = self.from_addr
            msg["To"] = audience
            msg.set_content(body)
            with smtplib.SMTP(self.host, self.port, timeout=30) as smtp:
                smtp.starttls()
                smtp.login(self.user, self.password)
                smtp.send_message(msg)
            delivered = True

        self._log_bq(
            product=product or "unknown",
            cadence=cadence or "unknown",
            period_date=period_date,
            subject=subject,
            body=body,
            audience=audience,
            delivered=delivered,
        )
        return delivered

    def _log_bq(
        self,
        *,
        product: str,
        cadence: str,
        period_date: str | date | None,
        subject: str,
        body: str,
        audience: str,
        delivered: bool,
    ) -> None:
        """Best-effort append to marts_insights.digest_delivery (load job, no streaming)."""
        try:
            from google.cloud import bigquery

            from insights.integrations.bigquery.client import get_bigquery_client
            from insights.integrations.bigquery.config import BigQueryConfig

            cfg = BigQueryConfig.from_env()
            client = get_bigquery_client(cfg.project)
            table_id = f"{cfg.project}.{TABLE_ID_SUFFIX}"
            self._ensure_table(client, table_id)

            if isinstance(period_date, date):
                pdate = period_date.isoformat()
            elif period_date:
                pdate = str(period_date)[:10]
            else:
                pdate = date.today().isoformat()

            sent_at = datetime.now(timezone.utc)
            row = {
                "period_date": pdate,
                "product": product,
                "cadence": cadence,
                "channel": self.channel,
                "audience": audience,
                "subject": subject,
                "body_text": body,
                "delivered": delivered,
                "sent_at": sent_at.isoformat(),
            }
            staging_id = f"{table_id}_staging"
            load_config = bigquery.LoadJobConfig(
                schema=_schema(),
                write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
                source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
            )
            client.load_table_from_json([row], staging_id, job_config=load_config).result()
            # Append via INSERT (idempotent enough for MVP; one row per send)
            client.query(
                f"""
                INSERT INTO `{table_id}`
                SELECT * FROM `{staging_id}`
                """
            ).result()
        except Exception as exc:
            print(f"digest_delivery BQ log skipped: {exc}")

    @staticmethod
    def _ensure_table(client: Any, table_id: str) -> None:
        from google.cloud import bigquery

        try:
            client.get_table(table_id)
            return
        except Exception:
            pass
        table = bigquery.Table(table_id, schema=_schema())
        table.time_partitioning = bigquery.TimePartitioning(
            type_=bigquery.TimePartitioningType.DAY,
            field="period_date",
        )
        table.clustering_fields = ["product", "cadence"]
        client.create_table(table, exists_ok=True)


def _schema():
    from google.cloud import bigquery

    return [
        bigquery.SchemaField("period_date", "DATE", mode="REQUIRED"),
        bigquery.SchemaField("product", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("cadence", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("channel", "STRING"),
        bigquery.SchemaField("audience", "STRING"),
        bigquery.SchemaField("subject", "STRING"),
        bigquery.SchemaField("body_text", "STRING"),
        bigquery.SchemaField("delivered", "BOOL"),
        bigquery.SchemaField("sent_at", "TIMESTAMP", mode="REQUIRED"),
    ]
