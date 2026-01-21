"""Base viewset scaffolding for JSON:API resources."""

from typing import Any

from fastapi import Request

from fastapi_jsonapi.core.document import JSONAPIDocumentBuilder
from fastapi_jsonapi.utils.query_params import parse_query_params


class JSONAPIViewSet:
    """Base class providing JSON:API action hooks."""

    serializer_class: type | None = None
    data_layer: Any = None
    permission_classes: list[type] = []
    filter_backends: list[type] = []
    pagination_class: type | None = None
    document_builder_class: type = JSONAPIDocumentBuilder
    included_serializers: dict[str, type] = {}
    allowed_actions: list[str] = ["list", "retrieve", "create", "update", "destroy", "relationship", "related"]

    def get_serializer(self) -> Any:
        """Instantiate the serializer."""
        if not self.serializer_class:
            raise ValueError("serializer_class must be set.")
        return self.serializer_class()

    def get_document_builder(self) -> JSONAPIDocumentBuilder:
        """Instantiate the document builder."""
        return self.document_builder_class()

    def get_query_params(self, request: Request) -> dict[str, Any]:
        """Parse and normalize JSON:API query parameters."""
        params = parse_query_params(request.query_params)
        if self.serializer_class:
            params["resource_type"] = self.serializer_class.Meta.type_
        fields_map = params.get("fields", {})
        params["fields"] = fields_map
        return params

    def get_base_url(self, request: Request) -> str:
        """Return base URL that includes API prefix for link generation."""
        base_url = str(request.base_url).rstrip("/")
        if not self.serializer_class:
            return base_url
        type_path = f"/{self.serializer_class.Meta.type_}"
        path = request.url.path
        if type_path in path:
            prefix = path.rsplit(type_path, 1)[0]
            return f"{base_url}{prefix}"
        return base_url

    def get_included_serializer(self, relationship_path: str) -> Any | None:
        """Return serializer for a relationship path if configured."""
        serializer = self.included_serializers.get(relationship_path)
        if serializer is None:
            serializer = self.included_serializers.get(relationship_path.split(".")[-1])
        return serializer() if serializer else None

    def build_included(
        self, instance: Any, include_paths: list[str], base_url: str
    ) -> list[dict[str, Any]]:
        """Build included resource objects for a single instance."""
        included: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()

        for include_path in include_paths:
            parts = [part for part in include_path.split(".") if part]
            if not parts:
                continue

            current_objects = [instance]
            current_path: list[str] = []
            for index, relationship in enumerate(parts):
                current_path.append(relationship)
                next_objects: list[Any] = []
                for current in current_objects:
                    if not hasattr(current, relationship):
                        continue
                    related = getattr(current, relationship)
                    if related is None:
                        continue
                    if isinstance(related, list):
                        next_objects.extend(related)
                    else:
                        next_objects.append(related)

                current_objects = next_objects

                serializer = self.get_included_serializer(".".join(current_path))
                if serializer is None:
                    continue
                type_fields = {}
                include_fields = getattr(self, "_current_fields", {})
                if include_fields:
                    type_fields = include_fields
                for related_instance in current_objects:
                    resource = serializer.to_resource(
                        related_instance,
                        base_url=base_url,
                        fields=type_fields.get(serializer.Meta.type_) or None,
                    )
                    key = (resource.get("type", ""), resource.get("id", ""))
                    if key not in seen:
                        included.append(resource)
                        seen.add(key)
        return included

    async def before_list(self, request: Request, *args: Any, **kwargs: Any) -> dict[str, Any] | None:
        """Hook called before list action. Override to add pre-processing logic."""
        return None

    async def perform_list(
        self, request: Request, params: dict[str, Any], *args: Any, **kwargs: Any
    ) -> dict[str, Any]:
        """Perform the list action. Override to customize list behavior."""
        items = await self.data_layer.list(params=params)
        serializer = self.get_serializer()
        base_url = self.get_base_url(request)
        fields_map = params.get("fields", {})
        self._current_fields = fields_map
        paginator = self.pagination_class() if self.pagination_class else None
        page_items = (
            paginator.paginate_queryset(items, params) if paginator else items
        )
        included = []
        include_paths = params.get("include", [])
        if include_paths:
            for instance in page_items:
                included.extend(self.build_included(instance, include_paths, base_url))
        links = {"self": str(request.url)}
        meta = None
        if paginator:
            total = len(items)
            pagination_params = {**params, "base_url": str(request.url)}
            links.update(
                paginator.get_links(
                    total=total,
                    params=pagination_params,
                )
            )
            meta = paginator.get_meta(
                total=total,
                params=pagination_params,
            )
        # When include is used, ensure relationships are included in data objects
        resource_fields = fields_map.get(serializer.Meta.type_) or None
        
        # If include is specified, always include relationships in data objects
        # This allows clients to see which relationships are included
        if include_paths:
            # Extract relationship names from include paths
            relationship_names = set()
            for path in include_paths:
                # Get first-level relationships (e.g., "author" from "author" or "comments.author")
                first_part = path.split(".")[0]
                relationship_names.add(first_part)
            
            # Add relationship names to fields to ensure they're included
            if relationship_names:
                if resource_fields:
                    # Merge relationship names with existing fields
                    resource_fields = list(set(resource_fields) | relationship_names)
                else:
                    # If no sparse fieldsets specified, relationships will be included by default
                    # But we set resource_fields to None to include all relationships
                    resource_fields = None
        
        document = self.get_document_builder().build_collection(
            serializer.to_many(
                page_items,
                base_url=base_url,
                fields=resource_fields,
            ),
            included=included if included else None,
            links=links,
            meta=meta,
        )
        return document

    async def after_list(
        self, request: Request, document: dict[str, Any], *args: Any, **kwargs: Any
    ) -> dict[str, Any]:
        """Hook called after list action. Override to add post-processing logic."""
        return document

    async def list(self, request: Request, *args: Any, **kwargs: Any) -> Any:
        """Handle GET collection requests."""
        # Before hook
        before_result = await self.before_list(request, *args, **kwargs)
        if before_result is not None:
            return before_result
        
        # Perform action
        params = self.get_query_params(request)
        document = await self.perform_list(request, params, *args, **kwargs)
        
        # After hook
        document = await self.after_list(request, document, *args, **kwargs)
        return document

    async def before_retrieve(
        self, request: Request, resource_id: str, *args: Any, **kwargs: Any
    ) -> dict[str, Any] | None:
        """Hook called before retrieve action. Override to add pre-processing logic."""
        return None

    async def perform_retrieve(
        self, request: Request, resource_id: str, params: dict[str, Any], *args: Any, **kwargs: Any
    ) -> dict[str, Any]:
        """Perform the retrieve action. Override to customize retrieve behavior."""
        instance = await self.data_layer.retrieve(resource_id=resource_id, params=params)
        serializer = self.get_serializer()
        base_url = self.get_base_url(request)
        fields_map = params.get("fields", {})
        self._current_fields = fields_map
        include_paths = params.get("include", [])
        included = (
            self.build_included(instance, include_paths, base_url) if include_paths else None
        )
        # When include is used, ensure relationships are included in data objects
        resource_fields = fields_map.get(serializer.Meta.type_) or None
        
        # If include is specified, always include relationships in data objects
        if include_paths:
            # Extract relationship names from include paths
            relationship_names = set()
            for path in include_paths:
                # Get first-level relationships (e.g., "author" from "author" or "comments.author")
                first_part = path.split(".")[0]
                relationship_names.add(first_part)
            
            # Add relationship names to fields to ensure they're included
            if relationship_names:
                if resource_fields:
                    # Merge relationship names with existing fields
                    resource_fields = list(set(resource_fields) | relationship_names)
                else:
                    # If no sparse fieldsets specified, relationships will be included by default
                    resource_fields = None
        
        document = self.get_document_builder().build_single(
            serializer.to_resource(
                instance,
                base_url=base_url,
                fields=resource_fields,
            ),
            included=included,
            links={"self": str(request.url)},
        )
        return document

    async def after_retrieve(
        self, request: Request, resource_id: str, document: dict[str, Any], *args: Any, **kwargs: Any
    ) -> dict[str, Any]:
        """Hook called after retrieve action. Override to add post-processing logic."""
        return document

    async def retrieve(self, request: Request, resource_id: str, *args: Any, **kwargs: Any) -> Any:
        """Handle GET single resource requests."""
        # Before hook
        before_result = await self.before_retrieve(request, resource_id, *args, **kwargs)
        if before_result is not None:
            return before_result
        
        # Perform action
        params = self.get_query_params(request)
        document = await self.perform_retrieve(request, resource_id, params, *args, **kwargs)
        
        # After hook
        document = await self.after_retrieve(request, resource_id, document, *args, **kwargs)
        return document

    async def before_relationship(
        self, request: Request, resource_id: str, relationship: str, *args: Any, **kwargs: Any
    ) -> dict[str, Any] | None:
        """Hook called before relationship action. Override to add pre-processing logic."""
        return None

    async def perform_relationship(
        self,
        request: Request,
        resource_id: str,
        relationship: str,
        params: dict[str, Any],
        *args: Any,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Perform the relationship action. Override to customize relationship behavior."""
        # Ensure the relationship is loaded
        params["include"] = [relationship]
        # Mark this as a relationship-only query to optimize loading (only id fields needed)
        params["relationship_only"] = True
        instance = await self.data_layer.retrieve(resource_id=resource_id, params=params)
        serializer = self.get_serializer()
        base_url = self.get_base_url(request)
        relationship_object = serializer.relationship_object(
            instance, relationship, base_url=base_url
        )
        if relationship_object is None:
            raise ValueError(f"Unknown relationship '{relationship}'.")
        return relationship_object

    async def after_relationship(
        self,
        request: Request,
        resource_id: str,
        relationship: str,
        relationship_object: dict[str, Any],
        *args: Any,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Hook called after relationship action. Override to add post-processing logic."""
        return relationship_object

    async def relationship(
        self, request: Request, resource_id: str, relationship: str, *args: Any, **kwargs: Any
    ) -> Any:
        """Handle GET relationship linkage requests."""
        # Before hook
        before_result = await self.before_relationship(request, resource_id, relationship, *args, **kwargs)
        if before_result is not None:
            return before_result
        
        # Perform action
        params = self.get_query_params(request)
        relationship_object = await self.perform_relationship(
            request, resource_id, relationship, params, *args, **kwargs
        )
        
        # After hook
        relationship_object = await self.after_relationship(
            request, resource_id, relationship, relationship_object, *args, **kwargs
        )
        return relationship_object

    async def before_related(
        self, request: Request, resource_id: str, relationship: str, *args: Any, **kwargs: Any
    ) -> dict[str, Any] | None:
        """Hook called before related action. Override to add pre-processing logic."""
        return None

    async def perform_related(
        self,
        request: Request,
        resource_id: str,
        relationship: str,
        params: dict[str, Any],
        *args: Any,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Perform the related action. Override to customize related behavior."""
        # Load the main resource and the relationship
        params["include"] = [relationship]
        instance = await self.data_layer.retrieve(resource_id=resource_id, params=params)
        
        # Get the relationship from the instance
        try:
            from sqlalchemy.inspection import inspect
            mapper = inspect(instance.__class__)
            rel = mapper.relationships.get(relationship)
            if rel is None:
                raise ValueError(f"Unknown relationship '{relationship}'.")
            
            related_objects = getattr(instance, relationship, None)
            is_to_many = rel.uselist
            
            # Handle to-one vs to-many relationships
            if is_to_many:
                if related_objects is None:
                    related_objects = []
                # Ensure it's a list
                if not isinstance(related_objects, list):
                    related_objects = list(related_objects) if related_objects else []
            else:
                # To-one relationship - convert to list for processing, but remember it's single
                if related_objects is None:
                    related_objects = []
                else:
                    related_objects = [related_objects]
        except Exception as e:
            raise ValueError(f"Error accessing relationship '{relationship}': {str(e)}")
        
        # Get serializer for the related resources
        related_serializer = self.get_included_serializer(relationship)
        if related_serializer is None:
            # Try to infer serializer from relationship model
            try:
                related_model = rel.mapper.class_
                # Look for serializer in included_serializers by model name
                for key, serializer_class in self.included_serializers.items():
                    if hasattr(serializer_class, "Meta") and hasattr(serializer_class.Meta, "model"):
                        if serializer_class.Meta.model == related_model:
                            related_serializer = serializer_class()
                            break
            except Exception:
                pass
        
        if related_serializer is None:
            raise ValueError(
                f"No serializer found for relationship '{relationship}'. "
                f"Add it to included_serializers."
            )
        
        base_url = self.get_base_url(request)
        fields_map = params.get("fields", {})
        self._current_fields = fields_map
        
        # Apply pagination if configured
        paginator = self.pagination_class() if self.pagination_class else None
        page_items = (
            paginator.paginate_queryset(related_objects, params) if paginator else related_objects
        )
        
        # Serialize related resources
        related_type = related_serializer.Meta.type_
        
        # Build included resources if nested includes are requested
        included = []
        include_paths = params.get("include", [])
        if include_paths:
            # Filter out the current relationship from include paths
            nested_includes = [
                path for path in include_paths
                if path != relationship and path.startswith(f"{relationship}.")
            ]
            if nested_includes:
                for related_instance in page_items:
                    nested_paths = [path[len(relationship) + 1:] for path in nested_includes]
                    included.extend(
                        self.build_included(related_instance, nested_paths, base_url)
                    )
        
        # Build links
        links = {"self": str(request.url)}
        
        # Handle to-one vs to-many relationships
        if is_to_many:
            # To-many: return collection document
            serialized_resources = related_serializer.to_many(
                page_items,
                base_url=base_url,
                fields=fields_map.get(related_type) or None,
            )
            if paginator:
                links.update(
                    paginator.get_links(
                        total=len(related_objects),
                        params={**params, "base_url": str(request.url)},
                    )
                )
            document = self.get_document_builder().build_collection(
                serialized_resources,
                included=included if included else None,
                links=links,
            )
        else:
            # To-one: return single resource document (or null)
            if page_items:
                serialized_resource = related_serializer.to_resource(
                    page_items[0],
                    base_url=base_url,
                    fields=fields_map.get(related_type) or None,
                )
                document = self.get_document_builder().build_single(
                    serialized_resource,
                    included=included if included else None,
                    links=links,
                )
            else:
                # Return null for to-one relationship when not set
                document = {"data": None, "links": links}
                if included:
                    document["included"] = included
        
        return document

    async def after_related(
        self,
        request: Request,
        resource_id: str,
        relationship: str,
        document: dict[str, Any],
        *args: Any,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Hook called after related action. Override to add post-processing logic."""
        return document

    async def related(
        self, request: Request, resource_id: str, relationship: str, *args: Any, **kwargs: Any
    ) -> Any:
        """Handle GET related resource requests (returns full resource objects, not just identifiers)."""
        # Before hook
        before_result = await self.before_related(request, resource_id, relationship, *args, **kwargs)
        if before_result is not None:
            return before_result
        
        # Perform action
        params = self.get_query_params(request)
        document = await self.perform_related(
            request, resource_id, relationship, params, *args, **kwargs
        )
        
        # After hook
        document = await self.after_related(request, resource_id, relationship, document, *args, **kwargs)
        return document

    async def before_create(self, request: Request, *args: Any, **kwargs: Any) -> dict[str, Any] | None:
        """Hook called before create action. Override to add pre-processing logic."""
        return None

    async def perform_create(
        self, request: Request, payload: dict[str, Any], *args: Any, **kwargs: Any
    ) -> dict[str, Any]:
        """Perform the create action. Override to customize create behavior."""
        instance = await self.data_layer.create(payload=payload)
        serializer = self.get_serializer()
        document = self.get_document_builder().build_single(serializer.to_resource(instance))
        return document

    async def after_create(
        self, request: Request, document: dict[str, Any], *args: Any, **kwargs: Any
    ) -> dict[str, Any]:
        """Hook called after create action. Override to add post-processing logic."""
        return document

    async def create(self, request: Request, *args: Any, **kwargs: Any) -> Any:
        """Handle POST create requests."""
        # Before hook
        before_result = await self.before_create(request, *args, **kwargs)
        if before_result is not None:
            return before_result
        
        # Perform action
        payload = await request.json()
        document = await self.perform_create(request, payload, *args, **kwargs)
        
        # After hook
        document = await self.after_create(request, document, *args, **kwargs)
        return document

    async def before_update(
        self, request: Request, resource_id: str, *args: Any, **kwargs: Any
    ) -> dict[str, Any] | None:
        """Hook called before update action. Override to add pre-processing logic."""
        return None

    async def perform_update(
        self,
        request: Request,
        resource_id: str,
        payload: dict[str, Any],
        *args: Any,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Perform the update action. Override to customize update behavior."""
        instance = await self.data_layer.update(resource_id=resource_id, payload=payload)
        serializer = self.get_serializer()
        document = self.get_document_builder().build_single(serializer.to_resource(instance))
        return document

    async def after_update(
        self,
        request: Request,
        resource_id: str,
        document: dict[str, Any],
        *args: Any,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Hook called after update action. Override to add post-processing logic."""
        return document

    async def update(self, request: Request, resource_id: str, *args: Any, **kwargs: Any) -> Any:
        """Handle PATCH update requests."""
        # Before hook
        before_result = await self.before_update(request, resource_id, *args, **kwargs)
        if before_result is not None:
            return before_result
        
        # Perform action
        payload = await request.json()
        document = await self.perform_update(request, resource_id, payload, *args, **kwargs)
        
        # After hook
        document = await self.after_update(request, resource_id, document, *args, **kwargs)
        return document

    async def before_destroy(
        self, request: Request, resource_id: str, *args: Any, **kwargs: Any
    ) -> dict[str, Any] | None:
        """Hook called before destroy action. Override to add pre-processing logic."""
        return None

    async def perform_destroy(
        self, request: Request, resource_id: str, *args: Any, **kwargs: Any
    ) -> dict[str, Any]:
        """Perform the destroy action. Override to customize destroy behavior."""
        await self.data_layer.delete(resource_id=resource_id)
        return {"meta": {"deleted": True}}

    async def after_destroy(
        self,
        request: Request,
        resource_id: str,
        result: dict[str, Any],
        *args: Any,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Hook called after destroy action. Override to add post-processing logic."""
        return result

    async def destroy(self, request: Request, resource_id: str, *args: Any, **kwargs: Any) -> Any:
        """Handle DELETE requests."""
        # Before hook
        before_result = await self.before_destroy(request, resource_id, *args, **kwargs)
        if before_result is not None:
            return before_result
        
        # Perform action
        result = await self.perform_destroy(request, resource_id, *args, **kwargs)
        
        # After hook
        result = await self.after_destroy(request, resource_id, result, *args, **kwargs)
        return result
