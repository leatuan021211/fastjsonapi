"""SQLAlchemy helper templates for filtering, sorting, and includes."""

from __future__ import annotations

from typing import Any, Callable

from sqlalchemy import and_, asc, desc, exists, or_, select
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import joinedload, load_only, selectinload


# Operator mapping for filter expressions
FILTER_OPERATORS: dict[str, Callable[[Any, Any], Any]] = {
    # Comparison operators
    "eq": lambda col, val: col == val,
    "ne": lambda col, val: col != val,
    "neq": lambda col, val: col != val,
    "!=": lambda col, val: col != val,
    "gt": lambda col, val: col > val,
    "gte": lambda col, val: col >= val,
    "ge": lambda col, val: col >= val,
    "lt": lambda col, val: col < val,
    "lte": lambda col, val: col <= val,
    "le": lambda col, val: col <= val,
    # Pattern matching
    "ilike": lambda col, val: col.ilike(val),
    "like": lambda col, val: col.ilike(val),
    # Membership operators
    "in": lambda col, val: col.in_(val if isinstance(val, list) else [val]),
    "not_in": lambda col, val: ~col.in_(val if isinstance(val, list) else [val]),
    "nin": lambda col, val: ~col.in_(val if isinstance(val, list) else [val]),
    # Null checks
    "is_null": lambda col, val: col.is_(None),
    "null": lambda col, val: col.is_(None),
    "is_not_null": lambda col, val: col.isnot(None),
    "not_null": lambda col, val: col.isnot(None),
    # Range operator (requires special handling)
    "between": lambda col, val: (
        col.between(val[0], val[1]) if isinstance(val, list) and len(val) == 2 else None
    ),
}


class SQLAlchemyQueryHelper:
    """Apply JSON:API query parameters to SQLAlchemy queries."""

    def __init__(self, *, model: Any) -> None:
        self.model = model

    def _columns_for_fields(
        self, model: Any, fields: list[str] | None
    ) -> list[Any]:
        mapper = inspect(model)
        if not fields:
            return []
        columns = []
        field_set = set(fields)
        for column in mapper.columns:
            if column.key in field_set:
                columns.append(getattr(model, column.key))
        for pk in mapper.primary_key:
            if pk.key not in field_set:
                columns.append(getattr(model, pk.key))
        return columns

    def _resolve_column(
        self, query: Any, field_path: str, join_paths: set[str]
    ) -> tuple[Any, Any | None]:
        """Resolve a field path (potentially nested) to a SQLAlchemy column.
        
        Handles nested relationships like 'comment.author.id':
        - For to-one relationships: uses joins
        - For to-many relationships: uses exists() subquery to avoid duplicates
        
        Returns (query, column) tuple.
        """
        if "." not in field_path:
            if hasattr(self.model, field_path):
                return query, getattr(self.model, field_path)
            return query, None

        parts = field_path.split(".")
        current_model = self.model
        current_query = query
        join_chain: list[str] = []
        
        # Check if any relationship in the path is to-many
        to_many_index = None
        for i, relationship_name in enumerate(parts[:-1]):
            if not hasattr(current_model, relationship_name):
                return current_query, None
            relationship_attr = getattr(current_model, relationship_name)
            rel_property = getattr(relationship_attr, "property", None)
            
            # Check if this is a to-many relationship
            if rel_property and rel_property.uselist:
                to_many_index = i
                break
            
            join_chain.append(relationship_name)
            join_key = ".".join(join_chain)
            if join_key not in join_paths:
                current_query = current_query.join(relationship_attr)
                join_paths.add(join_key)
            
            related_model = getattr(getattr(rel_property, "mapper", None), "class_", None)
            if related_model is None:
                return current_query, None
            current_model = related_model

        field_name = parts[-1]
        
        # If we found a to-many relationship, use exists() subquery
        if to_many_index is not None:
            # Build path up to the to-many relationship
            to_many_rel_name = parts[to_many_index]
            to_many_rel_attr = None
            parent_model = self.model
            
            # Navigate to the to-many relationship
            for j in range(to_many_index):
                if not hasattr(parent_model, parts[j]):
                    return current_query, None
                rel_attr = getattr(parent_model, parts[j])
                rel_prop = getattr(rel_attr, "property", None)
                if rel_prop is None:
                    return current_query, None
                parent_model = rel_prop.mapper.class_
            
            if not hasattr(parent_model, to_many_rel_name):
                return current_query, None
            to_many_rel_attr = getattr(parent_model, to_many_rel_name)
            to_many_rel_prop = getattr(to_many_rel_attr, "property", None)
            if to_many_rel_prop is None:
                return current_query, None
            
            # Build subquery starting from the to-many relationship's model
            related_model = to_many_rel_prop.mapper.class_
            subquery = select(1).select_from(related_model)
            
            # Correlate subquery with outer query using foreign key
            # Get the parent model's table for correlation
            parent_table = inspect(parent_model).tables[0]
            # Correlate the subquery with the parent table
            subquery = subquery.correlate(parent_table)
            
            # Get the parent model's primary key column
            parent_pk_attr = inspect(parent_model).primary_key[0]
            parent_pk_col = parent_table.c[parent_pk_attr.key]
            
            # Find the foreign key column in the related model
            for fk_col in to_many_rel_prop.local_columns:
                # Correlate: fk_col == parent_pk_col (from outer query)
                subquery = subquery.where(fk_col == parent_pk_col)
                break
            
            # Traverse remaining path in subquery
            remaining_parts = parts[to_many_index + 1:]
            current_subquery_model = related_model
            
            for rel_name in remaining_parts[:-1]:
                if not hasattr(current_subquery_model, rel_name):
                    return current_query, None
                rel_attr = getattr(current_subquery_model, rel_name)
                rel_prop = getattr(rel_attr, "property", None)
                if rel_prop is None:
                    return current_query, None
                subquery = subquery.join(rel_attr)
                current_subquery_model = rel_prop.mapper.class_
            
            # Get the final field column
            if hasattr(current_subquery_model, field_name):
                final_column = getattr(current_subquery_model, field_name)
                # Store the column and subquery for later use in _build_expression
                # We'll return a special marker that _build_expression can recognize
                # For now, return the column wrapped in a tuple with the subquery
                return current_query, (final_column, subquery)
            return current_query, None
        
        # No to-many relationship found, use regular join
        if hasattr(current_model, field_name):
            return current_query, getattr(current_model, field_name)
        return current_query, None

    def _apply_sort_column(self, query: Any, column: Any, direction: str) -> Any:
        if direction == "desc":
            return query.order_by(desc(column))
        return query.order_by(asc(column))

    def _build_expression(
        self, query: Any, node: dict[str, Any], join_paths: set[str]
    ) -> tuple[Any, Any | None]:
        if "and" in node:
            expressions = []
            for child in node["and"]:
                query, expr = self._build_expression(query, child, join_paths)
                if expr is not None:
                    expressions.append(expr)
            return query, and_(*expressions) if expressions else None
        if "or" in node:
            expressions = []
            for child in node["or"]:
                query, expr = self._build_expression(query, child, join_paths)
                if expr is not None:
                    expressions.append(expr)
            return query, or_(*expressions) if expressions else None

        field = node.get("field")
        op = node.get("op", "eq")
        val = node.get("val")
        if not field:
            return query, None
        query, column = self._resolve_column(query, field, join_paths)
        if column is None:
            return query, None
        
        # Check if column is a tuple (column, subquery) for to-many relationships
        if isinstance(column, tuple) and len(column) == 2:
            subquery_column, subquery = column
            # Build the condition for the subquery column
            operator_func = FILTER_OPERATORS.get(op)
            if operator_func:
                try:
                    condition = operator_func(subquery_column, val)
                    if condition is not None:
                        # Add condition to subquery and return exists() expression
                        subquery = subquery.where(condition)
                        return query, exists(subquery)
                except Exception:
                    pass
            # Default to equality
            subquery = subquery.where(subquery_column == val)
            return query, exists(subquery)
        
        # Handle different operators using the operator mapping
        operator_func = FILTER_OPERATORS.get(op)
        if operator_func:
            try:
                expression = operator_func(column, val)
                if expression is not None:
                    return query, expression
            except Exception:
                # If operator function fails, fall back to default
                pass
        
        # Default to equality if operator not found or failed
        return query, column == val

    def apply_filters(self, query: Any, params: dict[str, Any]) -> Any:
        """Apply filter parameter family to the query.
        
        Supports multiple filter formats:
        1. Simple dict: {"field": "value"} -> field = value
        2. Dict with operators: {"field": {"op": "gt", "val": 10}}
        3. JSON array: [{"field": "name", "op": "ilike", "val": "%john%"}, ...]
        4. Complex nested: [{"or": [{"and": [...]}]}]
        
        When filter is a list, all items are combined with AND logic.
        """
        filters = params.get("filter", {})
        
        # Skip if filters is empty (empty dict, empty list, or None)
        if not filters or (isinstance(filters, dict) and not filters) or (isinstance(filters, list) and not filters):
            return query
        
        join_paths: set[str] = set()

        if isinstance(filters, dict):
            # Handle dict format: {"field": "value"} or {"field": {"op": "gt", "val": 10}}
            expressions = []
            for field, value in filters.items():
                if isinstance(value, dict) and "op" in value:
                    # Already in the correct format
                    query, expr = self._build_expression(
                        query,
                        {"field": field, **value},
                        join_paths,
                    )
                else:
                    # Simple field=value format
                    query, expr = self._build_expression(
                        query,
                        {"field": field, "op": "eq", "val": value},
                        join_paths,
                    )
                if expr is not None:
                    expressions.append(expr)
            if expressions:
                query = query.where(and_(*expressions))
        elif isinstance(filters, list):
            # Handle array format: combine all items with AND logic
            expressions = []
            for item in filters:
                if isinstance(item, dict):
                    query, expr = self._build_expression(query, item, join_paths)
                    if expr is not None:
                        expressions.append(expr)
            if expressions:
                query = query.where(and_(*expressions))
        elif isinstance(filters, str):
            # Handle simple string filter (fallback)
            # Try to parse as JSON
            try:
                import json
                parsed = json.loads(filters)
                if isinstance(parsed, (list, dict)):
                    return self.apply_filters(query, {**params, "filter": parsed})
            except (json.JSONDecodeError, TypeError):
                pass
        
        return query

    def apply_sorting(self, query: Any, params: dict[str, Any]) -> Any:
        """Apply sort parameters to the query."""
        sort_fields = params.get("sort", [])
        join_paths: set[str] = set()
        for entry in sort_fields:
            field = entry.get("field")
            if not field:
                continue
            if hasattr(self.model, field):
                column = getattr(self.model, field)
            else:
                query, column = self._resolve_column(query, field, join_paths)
                if column is None:
                    continue
            direction = entry.get("direction", "asc")
            query = self._apply_sort_column(query, column, direction)
        return query

    def apply_sparse_fields(self, query: Any, params: dict[str, Any]) -> Any:
        """Apply sparse fieldsets to the query."""
        fields = params.get("fields", {})
        type_key = params.get("resource_type") or getattr(self.model, "__tablename__", "")
        model_fields = fields.get(type_key, [])
        columns = self._columns_for_fields(self.model, model_fields)
        if columns:
            query = query.options(load_only(*columns))
        return query

    def apply_includes(self, query: Any, params: dict[str, Any]) -> Any:
        """Apply include parameter to eager-load relationships."""
        includes = params.get("include", [])
        fields_map = params.get("fields", {})
        relationship_only = params.get("relationship_only", False)
        
        for relation in includes:
            relationship_path = [part for part in relation.split(".") if part]
            if not relationship_path:
                continue

            current_model = self.model
            loader = None
            valid = True

            for relationship_name in relationship_path:
                if not hasattr(current_model, relationship_name):
                    valid = False
                    break
                relationship_attr = getattr(current_model, relationship_name)
                rel_property = getattr(relationship_attr, "property", None)
                related_model = getattr(getattr(rel_property, "mapper", None), "class_", None)
                if rel_property is None or related_model is None:
                    valid = False
                    break

                type_key = getattr(related_model, "__tablename__", "")
                
                # For relationship-only queries, only load id fields
                if relationship_only:
                    # Only load primary key columns (typically just 'id')
                    mapper = inspect(related_model)
                    columns = [getattr(related_model, pk.key) for pk in mapper.primary_key]
                else:
                    # Use sparse fieldsets if specified
                    fields = fields_map.get(type_key)
                    columns = self._columns_for_fields(related_model, fields)

                if loader is None:
                    if rel_property.uselist:
                        loader = selectinload(relationship_attr)
                    else:
                        loader = joinedload(relationship_attr)
                else:
                    if rel_property.uselist:
                        loader = loader.selectinload(relationship_attr)
                    else:
                        loader = loader.joinedload(relationship_attr)

                if columns:
                    loader = loader.options(load_only(*columns))
                current_model = related_model

            if valid and loader is not None:
                query = query.options(loader)
        return query
