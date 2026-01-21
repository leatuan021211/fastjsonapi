"""JSON:API document construction templates."""

from typing import Any, Iterable, Mapping


class JSONAPIDocumentBuilder:
    """Build JSON:API v1.1 documents from serialized data."""

    def build_single(
        self,
        resource: Mapping[str, Any],
        *,
        included: Iterable[Mapping[str, Any]] | None = None,
        links: Mapping[str, Any] | None = None,
        meta: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Return a JSON:API document for a single resource object."""
        document: dict[str, Any] = {"data": dict(resource)}
        if included:
            document["included"] = [dict(item) for item in included]
        if links:
            document["links"] = dict(links)
        if meta:
            document["meta"] = dict(meta)
        return document

    def build_collection(
        self,
        resources: Iterable[Mapping[str, Any]],
        *,
        included: Iterable[Mapping[str, Any]] | None = None,
        links: Mapping[str, Any] | None = None,
        meta: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Return a JSON:API document for a collection of resources."""
        document: dict[str, Any] = {"data": [dict(item) for item in resources]}
        if included:
            document["included"] = [dict(item) for item in included]
        if links:
            document["links"] = dict(links)
        if meta:
            document["meta"] = dict(meta)
        return document

    def build_error(self, errors: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
        """Return a JSON:API error document from error objects."""
        return {"errors": [dict(error) for error in errors]}
