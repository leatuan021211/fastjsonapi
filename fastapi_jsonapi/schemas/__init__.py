"""Pydantic schemas for JSON:API."""

from .resource import (
    JSONAPIResource,
    JSONAPIResourceIdentifier,
    JSONAPIDocument,
    JSONAPIErrorDocument,
)

__all__ = [
    "JSONAPIResource",
    "JSONAPIResourceIdentifier",
    "JSONAPIDocument",
    "JSONAPIErrorDocument",
]
