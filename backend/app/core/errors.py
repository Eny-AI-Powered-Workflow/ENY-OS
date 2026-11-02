import logging

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger(__name__)

INTERNAL_ERROR_DETAIL = (
    "Internal server error. The request could not be completed; please retry."
)


class UnhandledExceptionMiddleware:
    """Convert unhandled exceptions into a JSON 500 response.

    This middleware must be registered *inside* ``CORSMiddleware``. Starlette
    builds its stack in reverse registration order, so the middleware registered
    first ends up innermost. ``ServerErrorMiddleware`` sits outside the CORS layer,
    so an exception that escapes the application produces a 500 with no
    ``Access-Control-Allow-Origin`` header. Browsers discard such responses and the
    frontend reports a generic network error instead of the real failure.

    Rendering the error response from inside the CORS layer keeps the CORS headers
    attached, so clients receive a readable ``{"detail": ...}`` payload.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        response_started = False

        async def send_wrapper(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            logger.exception(
                "Unhandled exception while serving %s %s",
                scope.get("method"),
                scope.get("path"),
            )
            if response_started:
                # The status line is already on the wire; nothing can be salvaged.
                raise
            response = JSONResponse(
                status_code=500,
                content={"detail": INTERNAL_ERROR_DETAIL},
            )
            await response(scope, receive, send)
