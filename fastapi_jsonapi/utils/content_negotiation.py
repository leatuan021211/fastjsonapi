"""Helpers for JSON:API content negotiation."""

from __future__ import annotations

from typing import Any


def _split_parameters(value: str) -> list[str]:
    return [part.strip() for part in value.split(";") if part.strip()]


def _parse_param_value(value: str) -> list[str]:
    if value.startswith('"') and value.endswith('"'):
        value = value[1:-1]
    if not value:
        return []
    return value.split(" ")


def parse_jsonapi_media_type(content_type: str) -> dict[str, Any]:
    """Parse JSON:API media type parameters (ext/profile)."""
    parts = _split_parameters(content_type)
    media_type = parts[0].lower() if parts else ""
    params: dict[str, Any] = {"media_type": media_type, "ext": [], "profile": []}

    for param in parts[1:]:
        if "=" not in param:
            continue
        name, raw_value = param.split("=", 1)
        name = name.strip().lower()
        raw_value = raw_value.strip()
        if name in {"ext", "profile"}:
            params[name] = _parse_param_value(raw_value)
        else:
            params.setdefault("other_params", {})[name] = raw_value
    return params
