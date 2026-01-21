"""Base serializer template for JSON:API."""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from sqlalchemy.inspection import inspect
from sqlalchemy.orm.attributes import NO_VALUE


class JSONAPISerializer:
    """Serialize SQLAlchemy models into JSON:API resource objects."""

    class Meta:
        """Serializer metadata (type, model, fields)."""

        type_: str = ""
        model: Any = None
        fields: list[str] = []

    def to_resource(
        self,
        instance: Any,
        *,
        base_url: str | None = None,
        fields: list[str] | None = None,
    ) -> dict[str, Any]:
        """Serialize a model instance into a JSON:API resource object."""
        normalized_fields = fields or None
        attributes = self.get_attributes(instance, fields=normalized_fields)
        relationships = self.get_relationships(
            instance, base_url=base_url, fields=normalized_fields
        )
        resource: dict[str, Any] = {
            "type": self.Meta.type_,
            "id": self.get_id(instance),
        }
        if attributes:
            resource["attributes"] = attributes
        if relationships:
            resource["relationships"] = relationships
        if base_url:
            resource["links"] = {"self": self._resource_url(base_url, resource["id"])}
        return resource

    def to_many(
        self,
        instances: Iterable[Any],
        *,
        base_url: str | None = None,
        fields: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Serialize a collection of instances."""
        normalized_fields = fields or None
        return [
            self.to_resource(instance, base_url=base_url, fields=normalized_fields)
            for instance in instances
        ]

    def get_id(self, instance: Any) -> str:
        """Return the resource id as a string."""
        value = getattr(instance, "id", None)
        return "" if value is None else str(value)

    def get_attributes(
        self, instance: Any, *, fields: list[str] | None = None
    ) -> dict[str, Any]:
        """Return JSON:API attributes derived from serializer fields."""
        allowed_fields = set(fields) if fields else None
        if self.Meta.fields:
            base_fields = [field for field in self.Meta.fields if field != "id"]
            if allowed_fields is not None:
                base_fields = [field for field in base_fields if field in allowed_fields]
            return {field: getattr(instance, field) for field in base_fields}
        if hasattr(instance, "__dict__"):
            attrs = {
                key: value
                for key, value in instance.__dict__.items()
                if not key.startswith("_") and key != "id"
            }
            if allowed_fields is not None:
                attrs = {key: value for key, value in attrs.items() if key in allowed_fields}
            return attrs
        return {}

    def get_relationships(
        self,
        instance: Any,
        *,
        base_url: str | None = None,
        fields: list[str] | None = None,
    ) -> Mapping[str, Any]:
        """Return relationships for the resource (override in subclasses).
        
        Relationships are included based on sparse fieldsets:
        - If fields is None or empty: include all relationships
        - If fields is specified: only include relationships listed in fields
        - Relationships are always included if they have data, even if not in fields
        """
        if base_url is None:
            return {}
        
        # Sparse fieldsets: if fields is specified, only include relationships in the list
        # If fields is None or empty, include all relationships
        allowed_fields = set(fields) if fields else None
        
        try:
            mapper = inspect(instance.__class__)
        except Exception:
            return {}
        
        relationships: dict[str, Any] = {}
        for relationship in mapper.relationships:
            # If sparse fieldsets are specified, only include relationships in the list
            if allowed_fields is not None and relationship.key not in allowed_fields:
                continue
            
            relationship_links = self._relationship_links(
                base_url, self.get_id(instance), relationship.key
            )
            data_value = self._relationship_data(instance, relationship)
            
            # Include relationship object with data (or empty array/null if no data)
            relationships[relationship.key] = {
                "links": relationship_links,
                "data": data_value if data_value is not None and data_value != [] else ([] if relationship.uselist else None),
            }
        
        return relationships

    def relationship_object(
        self, instance: Any, relationship_name: str, *, base_url: str | None = None
    ) -> dict[str, Any] | None:
        """Build a JSON:API relationship object for a single relationship."""
        if base_url is None:
            return None
        try:
            mapper = inspect(instance.__class__)
        except Exception:
            return None
        rel = mapper.relationships.get(relationship_name)
        if rel is None:
            return None
        links = self._relationship_links(base_url, self.get_id(instance), relationship_name)
        data_value = self._relationship_data(instance, rel)
        return {
            "links": links,
            "data": data_value,
        }

    def _resource_url(self, base_url: str, resource_id: str) -> str:
        base = base_url.rstrip("/")
        return f"{base}/{self.Meta.type_}/{resource_id}"

    def _relationship_links(
        self, base_url: str, resource_id: str, relationship: str
    ) -> dict[str, str]:
        base = base_url.rstrip("/")
        resource_path = f"{base}/{self.Meta.type_}/{resource_id}"
        return {
            "self": f"{resource_path}/relationships/{relationship}",
            "related": f"{resource_path}/{relationship}",
        }

    def _relationship_data(self, instance: Any, relationship: Any) -> Any:
        try:
            state = inspect(instance)
            attr_state = state.attrs[relationship.key]
            if attr_state.loaded_value is NO_VALUE:
                return [] if relationship.uselist else None
        except Exception:
            return [] if relationship.uselist else None
        related = getattr(instance, relationship.key, None)
        if relationship.uselist:
            if not related:
                return []
            return [self._identifier(item) for item in related]
        if related is None:
            return None
        return self._identifier(related)

    def _identifier(self, related: Any) -> dict[str, str]:
        type_name = getattr(related, "__tablename__", related.__class__.__name__.lower())
        value = getattr(related, "id", None)
        return {"type": type_name, "id": "" if value is None else str(value)}
