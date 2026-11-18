from __future__ import annotations

import logging
import secrets

from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from automator.api.errors import error_body

logger = logging.getLogger(__name__)
REQUEST_ID_HEADER = "X-Request-Id"


def internal_error_response(request_id: str) -> JSONResponse:
    body = error_body("internal_error", "Unexpected server error")
    return JSONResponse(body, status_code=500, headers={REQUEST_ID_HEADER: request_id})


class InternalErrorMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        started = False

        async def tracked(message: Message) -> None:
            nonlocal started
            started = started or message["type"] == "http.response.start"
            await send(message)

        try:
            await self.app(scope, receive, tracked)
        except Exception as error:
            if started:
                raise
            request_id = secrets.token_hex(8)
            logger.error("unexpected %s in request %s", type(error).__name__, request_id)
            await internal_error_response(request_id)(scope, receive, send)
