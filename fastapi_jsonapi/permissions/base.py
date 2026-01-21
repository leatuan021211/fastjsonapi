"""Base permission class for JSON:API viewsets."""

from typing import Any


class BasePermission:
    """Define access control hooks for JSON:API actions."""

    async def has_permission(self, *args: Any, **kwargs: Any) -> bool:
        """Return True if the request has general access."""
        raise NotImplementedError

    async def has_object_permission(self, *args: Any, **kwargs: Any) -> bool:
        """Return True if the request has access to a specific object."""
        raise NotImplementedError
