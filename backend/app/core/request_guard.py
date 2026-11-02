# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/core/request_guard.py
import hmac
from threading import BoundedSemaphore

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class RequestBodyTooLarge(Exception):
    pass


class RequestGuardMiddleware:
    """Bound per-process request concurrency and inbound body size."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        max_body_bytes: int,
        max_concurrent_requests: int,
        production: bool,
        edge_shared_secret: str = "",
    ) -> None:
        self.app = app
        self.max_body_bytes = max_body_bytes
        self.request_slots = BoundedSemaphore(max_concurrent_requests)
        self.edge_shared_secret = edge_shared_secret.encode("utf-8")
        self.security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
        }
        if production:
            self.security_headers["Strict-Transport-Security"] = "max-age=31536000"

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        is_health_check = scope.get("path") == "/health"
        if self.edge_shared_secret and not is_health_check:
            provided_secrets = [
                value for name, value in scope.get("headers", [])
                if name.lower() == b"x-eny-edge-token"
            ]
            if (
                len(provided_secrets) != 1
                or not hmac.compare_digest(provided_secrets[0], self.edge_shared_secret)
            ):
                response = JSONResponse(
                    status_code=403,
                    content={"detail": "Request did not pass the trusted edge."},
                    headers={"Cache-Control": "no-store", **self.security_headers},
                )
                await response(scope, receive, send)
                return

        uses_request_slot = not is_health_check
        if uses_request_slot and not self.request_slots.acquire(blocking=False):
            response = JSONResponse(
                status_code=503,
                content={"detail": "Server is busy; retry shortly."},
                headers={
                    "Retry-After": "1",
                    "Cache-Control": "no-store",
                    **self.security_headers,
                },
            )
            await response(scope, receive, send)
            return

        response_started = False
        received_bytes = 0

        async def guarded_send(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
                headers = list(message.get("headers", []))
                headers.extend(
                    (name.lower().encode("ascii"), value.encode("ascii"))
                    for name, value in self.security_headers.items()
                )
                message = {**message, "headers": headers}
            await send(message)

        async def guarded_receive() -> Message:
            nonlocal received_bytes
            message = await receive()
            if message["type"] == "http.request":
                received_bytes += len(message.get("body", b""))
                if received_bytes > self.max_body_bytes:
                    raise RequestBodyTooLarge
            return message

        try:
            content_lengths = [
                value for name, value in scope.get("headers", [])
                if name.lower() == b"content-length"
            ]
            has_transfer_encoding = any(
                name.lower() == b"transfer-encoding"
                for name, _ in scope.get("headers", [])
            )
            if content_lengths and has_transfer_encoding:
                response = JSONResponse(
                    status_code=400,
                    content={"detail": "Conflicting request framing headers."},
                )
                await response(scope, receive, guarded_send)
                return
            if content_lengths:
                if len(set(content_lengths)) != 1 or not content_lengths[0].isdigit():
                    response = JSONResponse(
                        status_code=400,
                        content={"detail": "Invalid Content-Length header."},
                    )
                    await response(scope, receive, guarded_send)
                    return
                if int(content_lengths[0]) > self.max_body_bytes:
                    response = JSONResponse(
                        status_code=413,
                        content={"detail": "Request body exceeds the configured limit."},
                    )
                    await response(scope, receive, guarded_send)
                    return

            await self.app(scope, guarded_receive, guarded_send)
        except RequestBodyTooLarge:
            if response_started:
                raise
            response = JSONResponse(
                status_code=413,
                content={"detail": "Request body exceeds the configured limit."},
            )
            await response(scope, receive, guarded_send)
        finally:
            if uses_request_slot:
                self.request_slots.release()
