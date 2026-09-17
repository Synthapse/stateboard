"""SQL app extract (KIH / YCA) — read-only, PHI-safe columns only."""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlparse

from insights.domain.models import Product
from insights.integrations.app.writer import write_raw_and_dims


def _sqlalchemy_url(env_key: str) -> str | None:
    raw = os.getenv(env_key, "").strip()
    if not raw:
        return None
    # SQLAlchemy prefers postgresql://
    if raw.startswith("postgres://"):
        raw = "postgresql://" + raw[len("postgres://") :]
    return _rewrite_cloudsql_socket(raw)


def _rewrite_cloudsql_socket(url: str) -> str:
    """
    Cloud SQL URLs like postgresql://u:p@/db?host=/cloudsql/PROJECT:REGION:INSTANCE
    only work on GCP. Locally, rewrite to 127.0.0.1:PORT (Cloud SQL Auth Proxy).
    """
    from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

    if "/cloudsql/" not in url:
        return url
    if os.path.isdir("/cloudsql"):
        return url  # running with mounted Cloud SQL sockets

    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    host_q = (qs.get("host") or [None])[0] or ""
    instance = host_q.replace("/cloudsql/", "").strip("/") if host_q.startswith("/cloudsql/") else ""
    port = (
        os.getenv("CLOUDSQL_PROXY_PORT", "").strip()
        or os.getenv(f"{os.getenv('_PRODUCT_ENV_PREFIX', '')}DATABASE_PROXY_PORT", "").strip()
        or "5433"
    )
    # Drop host query param; use TCP to local proxy
    qs.pop("host", None)
    new_netloc = parsed.netloc
    if not parsed.hostname:
        # netloc is often "user:pass@" with empty host
        userinfo = parsed.netloc.rstrip("@")
        new_netloc = f"{userinfo}@127.0.0.1:{port}" if userinfo else f"127.0.0.1:{port}"
    else:
        new_netloc = parsed.netloc  # unexpected; leave
    new_query = urlencode({k: v[0] if len(v) == 1 else v for k, v in qs.items()}, doseq=True)
    rewritten = urlunparse(
        (parsed.scheme, new_netloc, parsed.path, parsed.params, new_query, parsed.fragment)
    )
    if instance:
        print(
            f"Cloud SQL socket URL → 127.0.0.1:{port} "
            f"(start: cloud-sql-proxy {instance} --port {port})"
        )
    return rewritten


def _list_public_tables(conn: Any) -> list[str]:
    rows = conn.execute(
        __import__("sqlalchemy").text(
            """
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            ORDER BY table_name
            """
        )
    ).fetchall()
    return [r[0] for r in rows]


def _pick_table(tables: list[str], candidates: list[str]) -> str | None:
    """Prefer exact name, then suffix/prefix; avoid loose substring (user⊂user_products)."""
    lower = {t.lower(): t for t in tables}
    for c in candidates:
        if c in lower:
            return lower[c]
    for c in candidates:
        for t in tables:
            tl = t.lower()
            if tl.endswith("_" + c) or tl.startswith(c + "_") or tl == c:
                return t
    return None


def _safe_user_rows(conn: Any, table: str, limit: int = 5000) -> list[dict[str, Any]]:
    """Select id + non-PHI name-ish columns if present."""
    sa = __import__("sqlalchemy")
    cols = {
        r[0].lower()
        for r in conn.execute(
            sa.text(
                """
                SELECT column_name FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = :t
                """
            ),
            {"t": table},
        ).fetchall()
    }
    id_col = next((c for c in ("id", "uuid", "user_id", "pk") if c in cols), None)
    if not id_col:
        return []
    name_col = next(
        (c for c in ("username", "email", "display_name", "name", "full_name") if c in cols),
        None,
    )
    # Never select password / token / clinical columns
    select = [id_col] + ([name_col] if name_col else [])
    extra = [c for c in ("created_at", "is_active", "role", "status") if c in cols][:3]
    select.extend(extra)
    # Quote identifiers that may be mixed-case; table name from information_schema
    sql = f'SELECT {", ".join(select)} FROM "{table}" LIMIT {int(limit)}'
    out = []
    for row in conn.execute(sa.text(sql)).mappings():
        rid = row[id_col]
        name = row.get(name_col) if name_col else None
        # Redact email local-part partially
        if name_col == "email" and isinstance(name, str) and "@" in name:
            local, _, domain = name.partition("@")
            name = (local[:2] + "***@" + domain) if local else "***@" + domain
        attrs = {k: _jsonable(row[k]) for k in extra if row.get(k) is not None}
        out.append({"id": rid, "name": str(name) if name is not None else None, "attributes": attrs})
    return out


def _safe_account_rows(conn: Any, table: str, limit: int = 5000) -> list[dict[str, Any]]:
    sa = __import__("sqlalchemy")
    cols = {
        r[0].lower()
        for r in conn.execute(
            sa.text(
                """
                SELECT column_name FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = :t
                """
            ),
            {"t": table},
        ).fetchall()
    }
    id_col = next(
        (c for c in ("id", "uuid", "org_id", "organization_id", "account_id", "pk") if c in cols),
        None,
    )
    if not id_col:
        return []
    name_col = next((c for c in ("name", "title", "slug", "company_name") if c in cols), None)
    select = [id_col] + ([name_col] if name_col else [])
    sql = f'SELECT {", ".join(select)} FROM "{table}" LIMIT {int(limit)}'
    out = []
    for row in conn.execute(sa.text(sql)).mappings():
        out.append(
            {
                "id": row[id_col],
                "name": str(row[name_col]) if name_col and row.get(name_col) is not None else None,
                "attributes": {},
            }
        )
    return out


def _jsonable(v: Any) -> Any:
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return v


def extract_sql_product(product: Product, env_key: str) -> list[dict[str, Any]]:
    url = _sqlalchemy_url(env_key)
    if not url:
        return [{"product": product.value, "status": "skipped_no_url", "env": env_key}]

    try:
        from sqlalchemy import create_engine
    except ImportError:
        return [{"product": product.value, "status": "error", "error": "sqlalchemy not installed"}]

    # Rewrite docker host for local Mac runs
    parsed = urlparse(url)
    host = parsed.hostname or ""
    if host == "host.docker.internal":
        url = url.replace("host.docker.internal", "127.0.0.1")

    results: list[dict[str, Any]] = []
    try:
        engine = create_engine(url, pool_pre_ping=True)
        with engine.connect() as conn:
            tables = _list_public_tables(conn)
            user_t = _pick_table(
                tables,
                [
                    "usr_auth_users",
                    "usr_users",
                    "users_user",
                    "auth_user",
                    "users",
                    "accounts_user",
                    "core_user",
                ],
            )
            acct_t = _pick_table(
                tables,
                [
                    "org_organizations",
                    "organizations_organization",
                    "accounts_account",
                    "organizations",
                    "accounts",
                    "orgs",
                    "tenants",
                    "companies",
                ],
            )
            if user_t:
                users = _safe_user_rows(conn, user_t)
                results.append(write_raw_and_dims(product=product.value, entity="user", rows=users))
            else:
                results.append(
                    {
                        "product": product.value,
                        "entity": "user",
                        "status": "no_user_table",
                        "tables_sample": tables[:30],
                    }
                )
            if acct_t:
                accts = _safe_account_rows(conn, acct_t)
                results.append(
                    write_raw_and_dims(product=product.value, entity="account", rows=accts)
                )
            else:
                results.append(
                    {
                        "product": product.value,
                        "entity": "account",
                        "status": "no_account_table",
                        "tables_sample": tables[:30],
                    }
                )
    except Exception as exc:
        results.append({"product": product.value, "status": "error", "error": str(exc)[:300]})
    return results


def extract_kih() -> list[dict[str, Any]]:
    return extract_sql_product(Product.KIH, "KIH_DATABASE_URL")


def extract_yca() -> list[dict[str, Any]]:
    return extract_sql_product(Product.YCA, "YCA_DATABASE_URL")
