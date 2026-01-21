"""JSON:API error handling middleware template."""

from typing import Any

from starlette.responses import JSONResponse


class ErrorHandlerMiddleware:
    """Convert exceptions into JSON:API error documents."""

    def __init__(self, app: Any) -> None:
        """Store the ASGI app for middleware chaining."""
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        """Handle exceptions and serialize JSON:API error documents."""
        try:
            await self.app(scope, receive, send)
        except Exception as exc:  # noqa: BLE001 - template handler
            response = JSONResponse(
                {
                    "errors": [
                        {
                            "status": "500",
                            "title": "Internal Server Error",
                            "detail": str(exc),
                        }
                    ]
                },
                status_code=500,
            )
            await response(scope, receive, send)
