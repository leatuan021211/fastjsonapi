"""Helpers for JSON:API query parameter parsing."""

from __future__ import annotations

import json
import re
from typing import Any, Mapping


def _split_csv(value: str) -> list[str]:
    return [item for item in (part.strip() for part in value.split(",")) if item]


def _maybe_parse_json(value: str) -> Any:
    """Parse JSON string if it looks like JSON, otherwise return as-is.
    
    Handles URL-encoded JSON strings and regular JSON strings.
    FastAPI may already decode URL-encoded values, but we handle both cases.
    """
    if not isinstance(value, str):
        return value
    
    stripped = value.strip()
    if not stripped:
        return value
    
    # Try parsing as-is first (FastAPI may have already decoded it)
    try:
        if stripped[0] in "[{":
            parsed = json.loads(stripped)
            return parsed
    except json.JSONDecodeError:
        pass
    
    # If that fails, try URL decoding first, then parsing
    try:
        from urllib.parse import unquote
        decoded = unquote(stripped)
        if decoded != stripped and decoded[0] in "[{":
            return json.loads(decoded)
    except (json.JSONDecodeError, Exception):
        pass
    
    return value


def parse_query_params(params: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize JSON:API query parameter families."""
    normalized: dict[str, Any] = {
        "include": [],
        "fields": {},
        "sort": [],
        "page": {},
        "filter": {},
    }

    for key, value in params.items():
        if value is None:
            continue
        raw_value = str(value)
        if key == "include":
            normalized["include"] = _split_csv(raw_value)
        elif key.startswith("fields[") and key.endswith("]"):
            resource_type = key[len("fields[") : -1]
            normalized["fields"][resource_type] = _split_csv(raw_value)
        elif key == "sort":
            sort_fields = _split_csv(raw_value)
            normalized["sort"] = [
                {"field": field.lstrip("-"), "direction": "desc" if field.startswith("-") else "asc"}
                for field in sort_fields
            ]
        elif key.startswith("page[") and key.endswith("]"):
            page_key = key[len("page[") : -1]
            try:
                normalized["page"][page_key] = int(raw_value)
            except ValueError:
                normalized["page"][page_key] = raw_value
        elif key.startswith("filter"):
            if key == "filter":
                # Parse filter as JSON if it's a JSON string (array or object)
                # FastAPI may have already URL-decoded it, but it's still a string
                parsed_filter = _maybe_parse_json(raw_value)
                
                # If it's a list or dict, store it directly
                if isinstance(parsed_filter, list):
                    normalized["filter"] = parsed_filter
                elif isinstance(parsed_filter, dict):
                    normalized["filter"] = parsed_filter
                elif isinstance(parsed_filter, str):
                    # Still a string - try to parse it as JSON one more time
                    # This handles cases where FastAPI decoded URL encoding but left it as string
                    try:
                        if parsed_filter.strip().startswith(("[", "{")):
                            parsed_filter = json.loads(parsed_filter)
                            normalized["filter"] = parsed_filter
                        else:
                            # Simple string value - treat as field=value filter
                            normalized["filter"] = {"value": parsed_filter}
                    except (json.JSONDecodeError, AttributeError):
                        # Simple string value
                        normalized["filter"] = {"value": parsed_filter}
                else:
                    # Fallback
                    normalized["filter"] = parsed_filter
            else:
                # Use regex to parse filter[field] and filter[field][op] syntax
                # Pattern matches: filter[field] or filter[field][op]
                # Examples: filter[title], filter[age][gt], filter[author.name][ilike]
                match = re.match(r"^filter\[([^\]]+)\](?:\[([^\]]+)\])?$", key)
                if match:
                    field_name = match.group(1)
                    op_name = match.group(2)  # None if not present
                    parsed_value = _maybe_parse_json(raw_value)
                    
                    if not isinstance(normalized["filter"], dict):
                        normalized["filter"] = {}
                    
                    if op_name:
                        # filter[field][op] syntax: {"field": {"op": "gt", "val": value}}
                        if field_name not in normalized["filter"]:
                            normalized["filter"][field_name] = {}
                        normalized["filter"][field_name]["op"] = op_name
                        
                        # For 'in', 'not_in', 'nin' operators, split comma-separated values
                        if op_name in ("in", "not_in", "nin", "between"):
                            if isinstance(parsed_value, str):
                                # Split comma-separated string into list
                                normalized["filter"][field_name]["val"] = _split_csv(parsed_value)
                            elif isinstance(parsed_value, list):
                                # Already a list, use as-is
                                normalized["filter"][field_name]["val"] = parsed_value
                            else:
                                # Single value, convert to list
                                normalized["filter"][field_name]["val"] = [parsed_value]
                        else:
                            normalized["filter"][field_name]["val"] = parsed_value
                    else:
                        # filter[field] syntax: {"field": value}
                        normalized["filter"][field_name] = parsed_value
                else:
                    # Fallback for other filter-related keys
                    parsed_value = _maybe_parse_json(raw_value)
                    if not isinstance(normalized["filter"], dict):
                        normalized["filter"] = {}
                    normalized["filter"][key] = parsed_value

    return normalized
