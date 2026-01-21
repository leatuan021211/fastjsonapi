"""Router scaffolding aligned with JSON:API routes."""

from typing import Any, Callable

from fastapi import APIRouter, Depends
from fastapi import Request


class JSONAPIRouter(APIRouter):
    """APIRouter wrapper for JSON:API viewsets."""

    def register_viewset(
        self,
        prefix: str,
        viewset: Any | Callable[..., Any],
        *,
        dependencies: list[Any] | None = None,
    ) -> None:
        """Register JSON:API routes for a viewset instance or factory function.
        
        Args:
            prefix: URL prefix for all routes (e.g., "/articles")
            viewset: Viewset instance or factory function that returns a viewset instance.
                    If a factory function is provided, it will be called per request with
                    dependency injection support.
            dependencies: Additional FastAPI dependencies to inject for all routes.
        
        Examples:
            # Register with a viewset instance (no dependency injection)
            viewset = ArticleViewSet(session)
            router.register_viewset("/articles", viewset)
            
            # Register with a factory function (with dependency injection)
            def get_article_viewset(session: AsyncSession = Depends(get_session)) -> ArticleViewSet:
                return ArticleViewSet(session)
            
            router.register_viewset("/articles", get_article_viewset)
            
            # Register with additional dependencies
            router.register_viewset(
                "/articles",
                get_article_viewset,
                dependencies=[Depends(check_permission)]
            )
        """
        # Check if viewset is a callable factory function or an instance
        # A factory function is callable but not a class and doesn't have viewset methods
        is_factory = (
            callable(viewset)
            and not isinstance(viewset, type)
            and not hasattr(viewset, "list")
            and not hasattr(viewset, "retrieve")
        )
        
        if is_factory:
            # Create wrapper functions that use dependency injection
            allowed_actions = ["list", "retrieve", "create", "update", "destroy", "relationship", "related"]
            
            # Try to get allowed_actions from the viewset class via return type annotation
            if hasattr(viewset, "__annotations__"):
                return_type = viewset.__annotations__.get("return", None)
                # Handle string annotations and actual types
                if return_type:
                    # If it's a string, try to resolve it (basic check)
                    if isinstance(return_type, str):
                        # For now, use default actions
                        pass
                    elif hasattr(return_type, "allowed_actions"):
                        allowed_actions = getattr(return_type, "allowed_actions", allowed_actions)
                    # Try to get from __origin__ for generic types
                    elif hasattr(return_type, "__origin__"):
                        pass
            
            # Create wrapper for list action
            if "list" in allowed_actions:
                async def list_wrapper(request: Request, viewset_instance: Any = Depends(viewset)) -> Any:
                    return await viewset_instance.list(request)
                
                self.add_jsonapi_route(
                    prefix,
                    list_wrapper,
                    methods=["GET"],
                    name=f"{prefix}_list",
                )
            
            # Create wrapper for create action
            if "create" in allowed_actions:
                async def create_wrapper(request: Request, viewset_instance: Any = Depends(viewset)) -> Any:
                    return await viewset_instance.create(request)
                
                self.add_jsonapi_route(
                    prefix,
                    create_wrapper,
                    methods=["POST"],
                    name=f"{prefix}_create",
                )
            
            detail_path = f"{prefix}/{{resource_id}}"
            
            # Create wrapper for retrieve action
            if "retrieve" in allowed_actions:
                async def retrieve_wrapper(
                    request: Request,
                    resource_id: str,
                    viewset_instance: Any = Depends(viewset),
                ) -> Any:
                    return await viewset_instance.retrieve(request, resource_id)
                
                self.add_jsonapi_route(
                    detail_path,
                    retrieve_wrapper,
                    methods=["GET"],
                    name=f"{prefix}_retrieve",
                )
            
            # Create wrapper for relationship action
            if "relationship" in allowed_actions:
                relationship_path = f"{detail_path}/relationships/{{relationship}}"
                
                async def relationship_wrapper(
                    request: Request,
                    resource_id: str,
                    relationship: str,
                    viewset_instance: Any = Depends(viewset),
                ) -> Any:
                    return await viewset_instance.relationship(request, resource_id, relationship)
                
                self.add_jsonapi_route(
                    relationship_path,
                    relationship_wrapper,
                    methods=["GET"],
                    name=f"{prefix}_relationship",
                )
            
            # Create wrapper for related action (get related resources)
            if "related" in allowed_actions:
                related_path = f"{detail_path}/{{relationship}}"
                
                async def related_wrapper(
                    request: Request,
                    resource_id: str,
                    relationship: str,
                    viewset_instance: Any = Depends(viewset),
                ) -> Any:
                    return await viewset_instance.related(request, resource_id, relationship)
                
                self.add_jsonapi_route(
                    related_path,
                    related_wrapper,
                    methods=["GET"],
                    name=f"{prefix}_related",
                )
            
            # Create wrapper for update action
            if "update" in allowed_actions:
                async def update_wrapper(
                    request: Request,
                    resource_id: str,
                    viewset_instance: Any = Depends(viewset),
                ) -> Any:
                    return await viewset_instance.update(request, resource_id)
                
                self.add_jsonapi_route(
                    detail_path,
                    update_wrapper,
                    methods=["PATCH"],
                    name=f"{prefix}_update",
                )
            
            # Create wrapper for destroy action
            if "destroy" in allowed_actions:
                async def destroy_wrapper(
                    request: Request,
                    resource_id: str,
                    viewset_instance: Any = Depends(viewset),
                ) -> Any:
                    return await viewset_instance.destroy(request, resource_id)
                
                self.add_jsonapi_route(
                    detail_path,
                    destroy_wrapper,
                    methods=["DELETE"],
                    name=f"{prefix}_destroy",
                )
        else:
            # Use viewset instance directly (backward compatible)
            allowed_actions = getattr(viewset, "allowed_actions", ["list", "retrieve", "create", "update", "destroy", "relationship", "related"])
            
            if "list" in allowed_actions:
                self.add_jsonapi_route(prefix, viewset.list, methods=["GET"], name=f"{prefix}_list")
            if "create" in allowed_actions:
                self.add_jsonapi_route(prefix, viewset.create, methods=["POST"], name=f"{prefix}_create")
            
            detail_path = f"{prefix}/{{resource_id}}"
            
            if "retrieve" in allowed_actions:
                self.add_jsonapi_route(detail_path, viewset.retrieve, methods=["GET"], name=f"{prefix}_retrieve")
            
            if "relationship" in allowed_actions:
                relationship_path = f"{detail_path}/relationships/{{relationship}}"
                self.add_jsonapi_route(
                    relationship_path,
                    viewset.relationship,
                    methods=["GET"],
                    name=f"{prefix}_relationship",
                )
            
            if "related" in allowed_actions:
                related_path = f"{detail_path}/{{relationship}}"
                self.add_jsonapi_route(
                    related_path,
                    viewset.related,
                    methods=["GET"],
                    name=f"{prefix}_related",
                )
            
            if "update" in allowed_actions:
                self.add_jsonapi_route(detail_path, viewset.update, methods=["PATCH"], name=f"{prefix}_update")
            if "destroy" in allowed_actions:
                self.add_jsonapi_route(detail_path, viewset.destroy, methods=["DELETE"], name=f"{prefix}_destroy")

    def register_view(
        self,
        path: str,
        view: Callable[..., Any],
        *,
        methods: list[str] | None = None,
        name: str | None = None,
        dependencies: list[Any] | None = None,
    ) -> None:
        """Register a single view function with optional dependencies.
        
        This method provides a flexible way to register individual view functions
        with dependency injection support. It's useful for registering custom
        endpoints or individual viewset methods with specific dependencies.
        
        Args:
            path: URL path for the route (e.g., "/articles" or "/articles/{resource_id}")
            view: View function to register. Can be a regular async function or
                 a function that uses FastAPI's Depends() for dependency injection.
            methods: HTTP methods for the route (defaults to ["GET"] if not provided)
            name: Route name for OpenAPI documentation
            dependencies: List of FastAPI dependencies to inject (e.g., [Depends(get_session)])
        
        Examples:
            # Register a simple function-based view
            async def list_articles(request: Request) -> dict:
                return {"data": []}
            
            router.register_view("/articles", list_articles, methods=["GET"])
            
            # Register a view with dependency injection
            async def get_article_viewset(session: AsyncSession = Depends(get_session)):
                return ArticleViewSet(session)
            
            async def list_articles_with_deps(
                request: Request,
                viewset: ArticleViewSet = Depends(get_article_viewset)
            ) -> dict:
                return await viewset.list(request)
            
            router.register_view(
                "/articles",
                list_articles_with_deps,
                methods=["GET"]
            )
            
            # Register with additional dependencies
            router.register_view(
                "/articles/{resource_id}",
                retrieve_article_with_deps,
                methods=["GET"],
                dependencies=[Depends(check_permission)]
            )
        """
        if methods is None:
            methods = ["GET"]
        
        # Register the route with dependencies
        self.add_api_route(
            path,
            view,
            methods=methods,
            name=name,
            dependencies=dependencies if dependencies else None,
        )

    def add_jsonapi_route(
        self,
        path: str,
        endpoint: Callable[..., Any],
        *,
        methods: list[str],
        name: str | None = None,
    ) -> None:
        """Add a route with JSON:API defaults (content type, responses)."""
        self.add_api_route(path, endpoint, methods=methods, name=name)
