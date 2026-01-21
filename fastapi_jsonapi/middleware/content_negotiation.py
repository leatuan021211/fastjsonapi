"""JSON:API content negotiation middleware template."""

from typing import Any

from starlette.responses import JSONResponse

from fastapi_jsonapi.utils.content_negotiation import parse_jsonapi_media_type


class ContentNegotiationMiddleware:
    """Ensure JSON:API media type for requests and responses."""

    def __init__(self, app: Any) -> None:
        """Store the ASGI app for middleware chaining."""
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        """Validate JSON:API headers before passing to downstream app."""
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "").upper()
        headers = {k.decode().lower(): v.decode() for k, v in scope.get("headers", [])}
        content_type = headers.get("content-type", "")
        accept = headers.get("accept", "")

        if method in {"POST", "PATCH"}:
            parsed = parse_jsonapi_media_type(content_type)
            if parsed["media_type"] != "application/vnd.api+json":
                response = JSONResponse(
                    {"errors": [{"status": "415", "title": "Unsupported Media Type"}]},
                    status_code=415,
                )
                await response(scope, receive, send)
                return
            if parsed.get("other_params"):
                response = JSONResponse(
                    {"errors": [{"status": "415", "title": "Unsupported Media Type"}]},
                    status_code=415,
                )
                await response(scope, receive, send)
                return

        if accept and "application/vnd.api+json" not in accept and "*/*" not in accept:
            response = JSONResponse(
                {"errors": [{"status": "406", "title": "Not Acceptable"}]},
                status_code=406,
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)
