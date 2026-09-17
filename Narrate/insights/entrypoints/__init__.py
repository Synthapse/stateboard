"""Entrypoints."""

from insights.entrypoints.handler import digest_http, digest_run

__all__ = ["digest_run", "digest_http"]
