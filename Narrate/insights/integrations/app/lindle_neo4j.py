"""Lindle Neo4j extract → dim_user / dim_account (orgs)."""

from __future__ import annotations

import os
from typing import Any

from insights.domain.models import Product
from insights.integrations.app.writer import write_raw_and_dims


def extract_lindle() -> list[dict[str, Any]]:
    uri = os.getenv("LINDLE_NEO4J_URI", "").strip()
    user = os.getenv("LINDLE_NEO4J_USER", "").strip()
    password = os.getenv("LINDLE_NEO4J_PASSWORD", "").strip()
    database = os.getenv("LINDLE_NEO4J_DATABASE", "").strip() or None
    if not uri or not user or not password:
        return [{"product": Product.LINDLE.value, "status": "skipped_no_neo4j_env"}]

    try:
        from neo4j import GraphDatabase
    except ImportError:
        return [{"product": Product.LINDLE.value, "status": "error", "error": "neo4j not installed"}]

    results: list[dict[str, Any]] = []
    driver = GraphDatabase.driver(uri, auth=(user, password))
    try:
        with driver.session(database=database) as session:
            # Discover labels
            labels = [
                r["label"]
                for r in session.run("CALL db.labels() YIELD label RETURN label LIMIT 50")
            ]
            user_label = next(
                (l for l in labels if l.lower() in ("user", "person", "accountuser")),
                None,
            )
            org_label = next(
                (l for l in labels if l.lower() in ("organization", "org", "account", "company", "tenant")),
                None,
            )

            if user_label:
                users = []
                q = f"""
                MATCH (n:`{user_label}`)
                RETURN coalesce(n.id, elementId(n)) AS id,
                       coalesce(n.name, n.email) AS name
                LIMIT 5000
                """
                for r in session.run(q):
                    name = r["name"]
                    if isinstance(name, str) and "@" in name:
                        local, _, domain = name.partition("@")
                        name = (local[:2] + "***@" + domain) if local else "***@" + domain
                    users.append({"id": r["id"], "name": name, "attributes": {"label": user_label}})
                results.append(
                    write_raw_and_dims(product=Product.LINDLE.value, entity="user", rows=users)
                )
            else:
                results.append(
                    {
                        "product": Product.LINDLE.value,
                        "entity": "user",
                        "status": "no_user_label",
                        "labels": labels,
                    }
                )

            if org_label:
                orgs = []
                q = f"""
                MATCH (n:`{org_label}`)
                RETURN coalesce(n.id, elementId(n)) AS id,
                       n.name AS name
                LIMIT 5000
                """
                for r in session.run(q):
                    orgs.append(
                        {
                            "id": r["id"],
                            "name": r["name"],
                            "attributes": {"label": org_label},
                        }
                    )
                results.append(
                    write_raw_and_dims(product=Product.LINDLE.value, entity="account", rows=orgs)
                )
            else:
                results.append(
                    {
                        "product": Product.LINDLE.value,
                        "entity": "account",
                        "status": "no_account_label",
                        "labels": labels,
                    }
                )
    except Exception as exc:
        results.append({"product": Product.LINDLE.value, "status": "error", "error": str(exc)[:300]})
    finally:
        driver.close()
    return results
