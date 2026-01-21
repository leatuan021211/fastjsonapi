"""Middleware templates for JSON:API."""

from .content_negotiation import ContentNegotiationMiddleware
from .error_handler import ErrorHandlerMiddleware

__all__ = ["ContentNegotiationMiddleware", "ErrorHandlerMiddleware"]
