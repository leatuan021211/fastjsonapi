"""Utility templates for JSON:API parsing and headers."""

from .content_negotiation import parse_jsonapi_media_type
from .query_params import parse_query_params

__all__ = ["parse_jsonapi_media_type", "parse_query_params"]
