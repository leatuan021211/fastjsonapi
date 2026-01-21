"""Standard JSON:API pagination strategy templates."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlencode, urlsplit, urlunsplit

from .base import PaginationBase


class StandardPagination(PaginationBase):
    """Template for page[offset]/page[limit] pagination."""

    def paginate_queryset(self, items: list[Any], params: dict[str, Any]) -> list[Any]:
        """Paginate based on page[offset] and page[limit]."""
        page = params.get("page", {})
        offset = int(page.get("offset", 0))
        limit = int(page.get("limit", 10))
        if offset < 0 or limit < 1:
            return items
        return items[offset : offset + limit]

    def get_links(self, *, total: int, params: dict[str, Any]) -> dict[str, str]:
        """Build pagination links for standard pagination."""
        base_url = params.get("base_url")
        page = params.get("page", {})
        offset = int(page.get("offset", 0))
        limit = int(page.get("limit", 10))
        if not base_url:
            return {}

        def build_url(page_offset: int) -> str:
            split = urlsplit(base_url)
            query_params = dict(page)
            query_params["offset"] = page_offset
            query_params["limit"] = limit
            query = urlencode({f"page[{k}]": v for k, v in query_params.items()})
            return urlunsplit((split.scheme, split.netloc, split.path, query, split.fragment))

        last_offset = max(0, (max(total - 1, 0) // limit) * limit)
        links = {
            "self": build_url(offset),
            "first": build_url(0),
            "last": build_url(last_offset),
        }
        prev_offset = offset - limit
        if prev_offset >= 0:
            links["prev"] = build_url(prev_offset)
        next_offset = offset + limit
        if next_offset <= last_offset:
            links["next"] = build_url(next_offset)
        return links

    def get_meta(self, *, total: int, params: dict[str, Any]) -> dict[str, Any]:
        """Build pagination metadata with total, limit, and offset."""
        page = params.get("page", {})
        offset = int(page.get("offset", 0))
        limit = int(page.get("limit", 10))
        
        return {
            "total": total,
            "limit": limit,
            "offset": offset,
        }
