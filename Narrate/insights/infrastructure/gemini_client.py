"""Shared Gemini helpers for Digests (fail-open callers)."""

from __future__ import annotations

import json
import os
import re
from typing import Any


def gemini_configured() -> bool:
    return bool(os.getenv("GEMINI_API_KEY", "").strip())


def generate_json(prompt: str, system: str) -> dict[str, Any]:
    """Call Gemini and parse a JSON object from the response text."""
    import google.generativeai as genai

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY unset")

    model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash-latest")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        model_name,
        system_instruction=system,
        generation_config={"response_mime_type": "application/json"},
    )
    response = model.generate_content(prompt)
    text = (response.text or "").strip()
    return _parse_json_object(text)


def _parse_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    return json.loads(text)
