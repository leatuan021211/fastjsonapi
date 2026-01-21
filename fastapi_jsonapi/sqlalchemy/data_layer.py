"""SQLAlchemy data layer templates for JSON:API."""

from __future__ import annotations

from typing import Any, Callable

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession


class SQLAlchemyDataLayer:
    """Bridge JSON:API viewsets with SQLAlchemy models."""

    def __init__(
        self,
        *,
        model: Any,
        session: Session | AsyncSession,
        query_helper: Any | None = None,
    ) -> None:
        """Store the SQLAlchemy model and session."""
        self.model = model
        self.session = session
        self.query_helper = query_helper

    async def _execute(self, statement: Any) -> Any:
        if isinstance(self.session, AsyncSession):
            result = await self.session.execute(statement)
            return result
        return self.session.execute(statement)

    async def _commit(self) -> None:
        if isinstance(self.session, AsyncSession):
            await self.session.commit()
        else:
            self.session.commit()

    async def _refresh(self, instance: Any) -> None:
        if isinstance(self.session, AsyncSession):
            await self.session.refresh(instance)
        else:
            self.session.refresh(instance)

    async def list(self, *, params: dict[str, Any] | None = None) -> list[Any]:
        """Return a list of model instances."""
        params = params or {}
        statement = select(self.model)
        if self.query_helper:
            statement = self.query_helper.apply_filters(statement, params)
            statement = self.query_helper.apply_sorting(statement, params)
            statement = self.query_helper.apply_sparse_fields(statement, params)
            statement = self.query_helper.apply_includes(statement, params)
        result = await self._execute(statement)
        return list(result.scalars().all())

    async def retrieve(self, *, resource_id: str, params: dict[str, Any] | None = None) -> Any:
        """Return a single model instance."""
        params = params or {}
        statement = select(self.model).where(self.model.id == resource_id)
        if self.query_helper:
            statement = self.query_helper.apply_sparse_fields(statement, params)
            statement = self.query_helper.apply_includes(statement, params)
        result = await self._execute(statement)
        instance = result.scalars().first()
        if instance is None:
            raise ValueError("Resource not found.")
        return instance

    async def create(self, *, payload: dict[str, Any]) -> Any:
        """Create and return a model instance."""
        attributes = payload.get("data", {}).get("attributes", {})
        relationship_ids = self._extract_relationship_ids(payload)
        instance = self.model(**{**attributes, **relationship_ids})
        self.session.add(instance)
        await self._commit()
        await self._refresh(instance)
        return instance

    async def update(self, *, resource_id: str, payload: dict[str, Any]) -> Any:
        """Update and return a model instance."""
        instance = await self.retrieve(resource_id=resource_id)
        attributes = payload.get("data", {}).get("attributes", {})
        relationship_ids = self._extract_relationship_ids(payload)
        for key, value in attributes.items():
            setattr(instance, key, value)
        for key, value in relationship_ids.items():
            setattr(instance, key, value)
        await self._commit()
        await self._refresh(instance)
        return instance

    async def delete(self, *, resource_id: str) -> None:
        """Delete a model instance."""
        instance = await self.retrieve(resource_id=resource_id)
        await self._delete(instance)

    async def _delete(self, instance: Any) -> None:
        if isinstance(self.session, AsyncSession):
            await self.session.delete(instance)
        else:
            self.session.delete(instance)
        await self._commit()

    def _extract_relationship_ids(self, payload: dict[str, Any]) -> dict[str, Any]:
        data = payload.get("data", {})
        relationships = data.get("relationships", {}) or {}
        relationship_ids: dict[str, Any] = {}
        for name, relationship in relationships.items():
            rel_data = relationship.get("data")
            if rel_data is None:
                continue
            if isinstance(rel_data, list):
                continue
            if not isinstance(rel_data, dict):
                continue
            rel_id = rel_data.get("id")
            if rel_id is None:
                continue
            attr_name = f"{name}_id"
            if hasattr(self.model, attr_name):
                relationship_ids[attr_name] = rel_id
        return relationship_ids
