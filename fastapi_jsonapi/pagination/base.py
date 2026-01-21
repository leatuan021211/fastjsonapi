"""Pagination base class for JSON:API links and meta."""

from typing import Any


class PaginationBase:
    """Define pagination API for JSON:API."""

    def paginate_queryset(
        self, items: list[Any], params: dict[str, Any]
    ) -> list[Any]:
        """Return a paginated slice of items."""
        raise NotImplementedError

    def get_links(self, *, total: int, params: dict[str, Any]) -> dict[str, str]:
        """Return JSON:API pagination links."""
        raise NotImplementedError

    def get_meta(self, *, total: int, params: dict[str, Any]) -> dict[str, Any]:
        """Return JSON:API pagination metadata (total, limit, offset, etc.)."""
        raise NotImplementedError
