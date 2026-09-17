"""HTTP health probes + exceptions → raw_health → staging → core + marts.reliability."""

from __future__ import annotations

import hashlib
import os
import time
from datetime import date, datetime, timezone
from typing import Any

import requests

from insights.domain.models import Product
from insights.integrations.bigquery.client import get_bigquery_client
from insights.integrations.bigquery.config import BigQueryConfig
from insights.integrations.products import PRODUCT_SOURCES

# Cloud Run HTTP services with known/default URLs (override via HEALTH_URL_<PRODUCT>_<NAME>)
# name must match dim_service seed (without product prefix).
DEFAULT_TARGETS: list[dict[str, Any]] = [
    {
        "id": "kih:dr-kiwi-app",
        "product": "kih",
        "name": "dr-kiwi-app",
        "url": "https://dr-kiwi-app-rocn5g3qfq-lm.a.run.app/admin",
    },
    {
        "id": "lindle:lindle-backend",
        "product": "lindle",
        "name": "lindle-backend",
        "url": "https://lindle-backend-ukddwnxkhq-lm.a.run.app/health",
    },
    {
        "id": "lindle:lindle-backend-agents",
        "product": "lindle",
        "name": "lindle-backend-agents",
        "url": "https://lindle-backend-agents-ukddwnxkhq-lm.a.run.app/health",
    },
    {
        "id": "lindle:procureiq",
        "product": "lindle",
        "name": "procureiq",
        "url": "https://procureiq-ukddwnxkhq-lm.a.run.app/health",
    },
    {
        "id": "yca:yca-ca-backend",
        "product": "yca",
        "name": "yca-ca-backend",
        "url": "https://yca-ca-backend-rg4bk3yria-lm.a.run.app/docs",
    },
    {
        "id": "yca:yca-ca-backend-2",
        "product": "yca",
        "name": "yca-ca-backend-2",
        "url": "https://yca-ca-backend-2-rg4bk3yria-lm.a.run.app/health",
    },
    {
        "id": "yca:yca-ca-auth",
        "product": "yca",
        "name": "yca-ca-auth",
        "url": "https://yca-ca-auth-rg4bk3yria-lm.a.run.app/health",
    },
    {
        "id": "yca:yca-ca-backend-payment",
        "product": "yca",
        "name": "yca-ca-backend-payment",
        # No /health yet; any HTTP response means Cloud Run is up (404 = route missing).
        "url": "https://yca-ca-backend-payment-rg4bk3yria-lm.a.run.app/",
        "mode": "reachable",
    },
]


def _env_url(product: str, name: str) -> str:
    key = f"HEALTH_URL_{product.upper()}_{name.upper().replace('-', '_')}"
    return os.getenv(key, "").strip()


def _targets(product: str | None = None) -> list[dict[str, Any]]:
    out = []
    for t in DEFAULT_TARGETS:
        if product and t["product"] != product:
            continue
        url = _env_url(t["product"], t["name"]) or t.get("url") or ""
        if not url:
            continue
        out.append({**t, "url": url})
    return out


def _probe(url: str, mode: str = "health", timeout: float = 8.0) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        resp = requests.get(
            url,
            timeout=timeout,
            proxies={"http": None, "https": None},
            allow_redirects=False,
        )
        latency_ms = round((time.perf_counter() - started) * 1000.0, 1)
        if mode == "reachable":
            ok = resp.status_code < 500
        else:
            ok = 200 <= resp.status_code < 400
        body_snip = (resp.text or "")[:200]
        return {
            "ok": ok,
            "status_code": resp.status_code,
            "latency_ms": latency_ms,
            "error": None if ok else f"HTTP {resp.status_code}: {body_snip}",
        }
    except Exception as exc:
        latency_ms = round((time.perf_counter() - started) * 1000.0, 1)
        return {
            "ok": False,
            "status_code": None,
            "latency_ms": latency_ms,
            "error": str(exc)[:300],
        }


def run_healthchecks(product: str | None = None) -> dict[str, Any]:
    """
    Probe services → raw_health + staging + core.fct_healthchecks / fct_exceptions
    + marts.reliability.
    """
    cfg = BigQueryConfig.from_env()
    client = get_bigquery_client(cfg.project)
    now = datetime.now(timezone.utc)
    today = date.today().isoformat()
    targets = _targets(product)
    if not targets:
        return {"status": "skipped", "reason": "no_health_urls", "probes": []}

    probes: list[dict[str, Any]] = []
    health_fct: list[dict[str, Any]] = []
    exc_fct: list[dict[str, Any]] = []
    raw_probe_rows: list[dict[str, Any]] = []
    raw_exc_rows: list[dict[str, Any]] = []
    stg_health: list[dict[str, Any]] = []
    stg_exc: list[dict[str, Any]] = []

    for t in targets:
        result = _probe(t["url"], mode=t.get("mode") or "health")
        probe = {"id": t["id"], "product": t["product"], "name": t["name"], "url": t["url"], **result}
        probes.append(probe)

        payload = {
            "url": t["url"],
            "status_code": result["status_code"],
            "latency_ms": result["latency_ms"],
            "error": result["error"],
            "service_name": t["name"],
            "ok": result["ok"],
        }
        record_id = f"{t['id']}:{now.strftime('%Y%m%d%H%M%S')}"
        raw_probe_rows.append(
            {
                "source_system": "health",
                "source_table": "http_probe",
                "ingest_date": today,
                "product": t["product"],
                "record_id": record_id,
                "event_ts": now.isoformat(),
                "payload_json": payload,
                "ingested_at": now.isoformat(),
            }
        )
        stg_health.append(
            {
                "source_system": "health",
                "source_table": "http_probe",
                "ingest_date": today,
                "product": t["product"],
                "record_id": record_id,
                "event_ts": now.isoformat(),
                "payload_json": payload,
                "ingested_at": now.isoformat(),
            }
        )
        health_fct.append(
            {
                "event_ts": now.isoformat(),
                "product": t["product"],
                "entity_id": t["id"],
                "metric_name": "healthcheck",
                "metric_value": float(result["latency_ms"]) if result["latency_ms"] is not None else None,
                "cost_usd": None,
                "status": "ok" if result["ok"] else "fail",
                "props_json": payload,
                "updated_at": now.isoformat(),
            }
        )

        if not result["ok"]:
            exc_payload = {
                "type": "healthcheck_fail",
                "service_name": t["name"],
                "message": result["error"] or "healthcheck failed",
                "status_code": result["status_code"],
                "url": t["url"],
                "source": "health_probe",
            }
            exc_id = f"{t['id']}:healthfail:{now.strftime('%Y%m%d%H%M%S')}"
            raw_exc_rows.append(
                {
                    "source_system": "health",
                    "source_table": "healthcheck_fail",
                    "ingest_date": today,
                    "product": t["product"],
                    "record_id": exc_id,
                    "event_ts": now.isoformat(),
                    "payload_json": exc_payload,
                    "ingested_at": now.isoformat(),
                }
            )
            stg_exc.append({**raw_exc_rows[-1]})
            exc_fct.append(
                {
                    "event_ts": now.isoformat(),
                    "product": t["product"],
                    "entity_id": t["id"],
                    "metric_name": "exception",
                    "metric_value": 1.0,
                    "cost_usd": None,
                    "status": "fail",
                    "props_json": exc_payload,
                    "updated_at": now.isoformat(),
                }
            )

    # Cloud Error Reporting (fail-open)
    erp = _pull_error_reporting(product, now, today)
    raw_exc_rows.extend(erp["raw"])
    stg_exc.extend(erp["staging"])
    exc_fct.extend(erp["fct"])

    _append_raw(client, cfg, f"{cfg.project}.raw_health.probes", raw_probe_rows)
    _append_raw(client, cfg, f"{cfg.project}.raw_health.exceptions", raw_exc_rows)
    _merge_staging(client, cfg, f"{cfg.project}.staging.stg_service_health", stg_health)
    _merge_staging(client, cfg, f"{cfg.project}.staging.stg_exceptions", stg_exc)
    _append_fct(client, cfg, f"{cfg.project}.core.fct_healthchecks", health_fct)
    _append_fct(client, cfg, f"{cfg.project}.core.fct_exceptions", exc_fct)

    mart = _promote_reliability(client, cfg, probes, exc_fct, now)
    return {
        "status": "ok",
        "probed": len(probes),
        "ok": sum(1 for p in probes if p["ok"]),
        "fail": sum(1 for p in probes if not p["ok"]),
        "exceptions": len(exc_fct),
        "error_reporting": erp["meta"],
        "probes": probes,
        "marts_reliability": mart,
        "raw_health": {"probes": len(raw_probe_rows), "exceptions": len(raw_exc_rows)},
    }


def _pull_error_reporting(
    product: str | None,
    now: datetime,
    today: str,
) -> dict[str, Any]:
    """Pull recent Error Reporting groups per product GCP project (fail-open)."""
    raw: list[dict[str, Any]] = []
    staging: list[dict[str, Any]] = []
    fct: list[dict[str, Any]] = []
    meta: list[dict[str, Any]] = []

    products = [Product(product)] if product else list(Product)
    try:
        import google.auth
        from google.auth.transport.requests import AuthorizedSession
    except ImportError:
        return {
            "raw": raw,
            "staging": staging,
            "fct": fct,
            "meta": [{"status": "skipped", "reason": "google.auth missing"}],
        }

    try:
        creds, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        session = AuthorizedSession(creds)
    except Exception as exc:
        return {
            "raw": raw,
            "staging": staging,
            "fct": fct,
            "meta": [{"status": "error", "error": f"adc:{exc}"[:200]}],
        }

    for p in products:
        sources = PRODUCT_SOURCES[p]
        gcp = sources.gcp_project_id
        try:
            url = (
                f"https://clouderrorreporting.googleapis.com/v1beta1/"
                f"projects/{gcp}/groupStats"
            )
            resp = session.get(
                url,
                params={"timeRange.period": "PERIOD_1_DAY", "pageSize": 25},
                timeout=20,
                headers={"x-goog-user-project": gcp},
            )
            if resp.status_code >= 400:
                meta.append(
                    {
                        "product": p.value,
                        "gcp_project": gcp,
                        "status": "error",
                        "error": f"HTTP {resp.status_code}: {resp.text[:160]}",
                    }
                )
                continue
            groups = (resp.json() or {}).get("errorGroupStats") or []
            n = 0
            for g in groups:
                n += 1
                group = g.get("group") or {}
                group_id = group.get("groupId") or f"err-{n}"
                rep = g.get("representative") or {}
                message = (rep.get("message") or "")[:300]
                count = int(g.get("count") or 0)
                fingerprint = hashlib.sha1(f"{gcp}:{group_id}".encode()).hexdigest()[:16]
                payload = {
                    "type": "error_reporting",
                    "gcp_project": gcp,
                    "group_id": group_id,
                    "message": message or group_id,
                    "count": count,
                    "source": "cloud_error_reporting",
                }
                rid = f"{p.value}:erp:{fingerprint}:{today}"
                row = {
                    "source_system": "gcp",
                    "source_table": "error_reporting",
                    "ingest_date": today,
                    "product": p.value,
                    "record_id": rid,
                    "event_ts": now.isoformat(),
                    "payload_json": payload,
                    "ingested_at": now.isoformat(),
                }
                raw.append(row)
                staging.append(row)
                fct.append(
                    {
                        "event_ts": now.isoformat(),
                        "product": p.value,
                        "entity_id": f"{p.value}:erp:{fingerprint}",
                        "metric_name": "exception",
                        "metric_value": float(count),
                        "cost_usd": None,
                        "status": "fail" if count else "ok",
                        "props_json": payload,
                        "updated_at": now.isoformat(),
                    }
                )
            meta.append({"product": p.value, "gcp_project": gcp, "status": "ok", "groups": n})
        except Exception as exc:
            meta.append(
                {
                    "product": p.value,
                    "gcp_project": gcp,
                    "status": "error",
                    "error": str(exc)[:200],
                }
            )

    return {"raw": raw, "staging": staging, "fct": fct, "meta": meta}


def _landing_schema():
    from google.cloud import bigquery

    return [
        bigquery.SchemaField("source_system", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("source_table", "STRING"),
        bigquery.SchemaField("ingest_date", "DATE", mode="REQUIRED"),
        bigquery.SchemaField("product", "STRING"),
        bigquery.SchemaField("record_id", "STRING"),
        bigquery.SchemaField("event_ts", "TIMESTAMP"),
        bigquery.SchemaField("payload_json", "JSON", mode="REQUIRED"),
        bigquery.SchemaField("ingested_at", "TIMESTAMP", mode="REQUIRED"),
    ]


def _ensure_raw_table(client: Any, table_id: str) -> None:
    from google.cloud import bigquery

    try:
        client.get_table(table_id)
        return
    except Exception:
        pass
    table = bigquery.Table(table_id, schema=_landing_schema())
    table.time_partitioning = bigquery.TimePartitioning(
        type_=bigquery.TimePartitioningType.DAY, field="ingest_date"
    )
    client.create_table(table, exists_ok=True)


def _append_raw(client: Any, cfg: BigQueryConfig, table_id: str, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    from google.cloud import bigquery

    _ensure_raw_table(client, table_id)
    staging = f"{table_id}_staging"
    client.load_table_from_json(
        rows,
        staging,
        job_config=bigquery.LoadJobConfig(
            schema=client.get_table(table_id).schema,
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
            source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        ),
    ).result()
    client.query(
        f"""
        MERGE `{table_id}` T
        USING `{staging}` S
        ON T.product = S.product AND T.record_id = S.record_id AND T.source_table = S.source_table
        WHEN MATCHED THEN UPDATE SET
          payload_json = S.payload_json,
          ingest_date = S.ingest_date,
          event_ts = S.event_ts,
          ingested_at = S.ingested_at
        WHEN NOT MATCHED THEN INSERT ROW
        """,
        location=cfg.location,
    ).result()


def _merge_staging(
    client: Any, cfg: BigQueryConfig, table_id: str, rows: list[dict[str, Any]]
) -> None:
    if not rows:
        return
    from google.cloud import bigquery

    staging = f"{table_id}_batch"
    dest = client.get_table(table_id)
    client.load_table_from_json(
        rows,
        staging,
        job_config=bigquery.LoadJobConfig(
            schema=dest.schema,
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
            source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        ),
    ).result()
    client.query(
        f"""
        MERGE `{table_id}` T
        USING `{staging}` S
        ON T.product = S.product AND T.record_id = S.record_id
           AND IFNULL(T.source_table, '') = IFNULL(S.source_table, '')
           AND T.ingest_date = S.ingest_date
        WHEN MATCHED THEN UPDATE SET
          payload_json = S.payload_json,
          event_ts = S.event_ts,
          ingested_at = S.ingested_at
        WHEN NOT MATCHED THEN INSERT ROW
        """,
        location=cfg.location,
    ).result()


def _append_fct(
    client: Any, cfg: BigQueryConfig, table_id: str, rows: list[dict[str, Any]]
) -> None:
    if not rows:
        return
    from google.cloud import bigquery

    staging = f"{table_id}_batch"
    dest = client.get_table(table_id)
    client.load_table_from_json(
        rows,
        staging,
        job_config=bigquery.LoadJobConfig(
            schema=dest.schema,
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
            source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        ),
    ).result()
    client.query(
        f"""
        INSERT INTO `{table_id}`
        SELECT * FROM `{staging}`
        """,
        location=cfg.location,
    ).result()


def _promote_reliability(
    client: Any,
    cfg: BigQueryConfig,
    probes: list[dict[str, Any]],
    exceptions: list[dict[str, Any]],
    now: datetime,
) -> dict[str, Any]:
    from google.cloud import bigquery

    by_product: dict[str, list[dict[str, Any]]] = {}
    for p in probes:
        by_product.setdefault(p["product"], []).append(p)

    exc_by_product: dict[str, list[dict[str, Any]]] = {}
    for e in exceptions:
        exc_by_product.setdefault(e["product"], []).append(e)

    # Include products that only have Error Reporting exceptions
    for p in exc_by_product:
        by_product.setdefault(p, [])

    today = date.today().isoformat()
    rows = []
    for product, items in by_product.items():
        ok_n = sum(1 for i in items if i["ok"])
        fail_n = len(items) - ok_n
        failing = [i["id"] for i in items if not i["ok"]]
        latencies = [i["latency_ms"] for i in items if i.get("latency_ms") is not None]
        exc_items = exc_by_product.get(product, [])
        top_types = []
        for e in exc_items[:5]:
            props = e.get("props_json") or {}
            top_types.append(props.get("type") or props.get("message") or "exception")
        rows.append(
            {
                "period_date": today,
                "product": product,
                "cadence": "daily",
                "metrics_json": {
                    "services_total": len(items),
                    "services_up": ok_n,
                    "services_down": fail_n,
                    "failing": failing,
                    "avg_latency_ms": round(sum(latencies) / len(latencies), 1) if latencies else None,
                    "exception_count": len(exc_items),
                    "exception_types": top_types,
                },
                "updated_at": now.isoformat(),
            }
        )

    if not rows:
        return {"status": "empty"}

    mart_id = f"{cfg.project}.marts.reliability"
    staging = f"{mart_id}_health_staging"
    dest = client.get_table(mart_id)
    client.load_table_from_json(
        rows,
        staging,
        job_config=bigquery.LoadJobConfig(
            schema=dest.schema,
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
            source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        ),
    ).result()
    client.query(
        f"""
        MERGE `{mart_id}` T
        USING `{staging}` S
        ON T.product = S.product
           AND T.period_date = S.period_date
           AND IFNULL(T.cadence, 'daily') = IFNULL(S.cadence, 'daily')
        WHEN MATCHED THEN UPDATE SET
          metrics_json = S.metrics_json,
          updated_at = S.updated_at
        WHEN NOT MATCHED THEN INSERT (period_date, product, cadence, metrics_json, updated_at)
        VALUES (S.period_date, S.product, S.cadence, S.metrics_json, S.updated_at)
        """,
        location=cfg.location,
    ).result()
    return {"status": "ok", "rows_upserted": len(rows)}
