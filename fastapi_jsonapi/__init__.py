"""FastAPI JSON:API v1.1 template package."""

from .core.document import JSONAPIDocumentBuilder
from .core.errors import JSONAPIErrorBuilder
from .routers.base import JSONAPIRouter
from .serializers.base import JSONAPISerializer
from .viewsets.base import JSONAPIViewSet

__all__ = [
    "JSONAPIDocumentBuilder",
    "JSONAPIErrorBuilder",
    "JSONAPIRouter",
    "JSONAPISerializer",
    "JSONAPIViewSet",
]
