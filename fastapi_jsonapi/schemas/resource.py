"""Pydantic schema templates for JSON:API v1.1 documents."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class JSONAPIResourceIdentifier(BaseModel):
    """Resource identifier object: type + id."""

    type: str
    id: str


class JSONAPIResource(BaseModel):
    """Resource object with attributes and relationships."""

    type: str
    id: Optional[str] = None
    attributes: Optional[Dict[str, Any]] = None
    relationships: Optional[Dict[str, Any]] = None


class JSONAPIDocument(BaseModel):
    """Top-level JSON:API document."""

    data: Optional[Any] = None
    included: Optional[List[JSONAPIResource]] = None
    meta: Optional[Dict[str, Any]] = None
    links: Optional[Dict[str, Any]] = None


class JSONAPIErrorDocument(BaseModel):
    """Top-level JSON:API error document."""

    errors: List[Dict[str, Any]]
