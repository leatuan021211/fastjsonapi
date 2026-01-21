"""JSON:API error object templates."""

from typing import Any


class JSONAPIErrorBuilder:
    """Build JSON:API error objects and error documents."""

    def error_object(
        self,
        *,
        status: str | None = None,
        code: str | None = None,
        title: str | None = None,
        detail: str | None = None,
        source: dict[str, Any] | None = None,
        meta: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Return a JSON:API error object."""
        error: dict[str, Any] = {}
        if status is not None:
            error["status"] = status
        if code is not None:
            error["code"] = code
        if title is not None:
            error["title"] = title
        if detail is not None:
            error["detail"] = detail
        if source is not None:
            error["source"] = source
        if meta is not None:
            error["meta"] = meta
        if not error:
            raise ValueError("Error object must include at least one field.")
        return error

    def error_document(self, errors: list[dict[str, Any]]) -> dict[str, Any]:
        """Return a JSON:API document with an errors array."""
        return {"errors": errors}
