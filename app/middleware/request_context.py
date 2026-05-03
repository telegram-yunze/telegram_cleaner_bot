from __future__ import annotations

from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class RequestContextMiddleware(BaseHTTPMiddleware):
    """为每个请求注入 request_id，并写回响应头。"""

    async def dispatch(self, request: Request, call_next) -> Response:
        incoming_request_id = request.headers.get("X-Request-ID")
        request_id = incoming_request_id.strip() if incoming_request_id else uuid4().hex
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


__all__ = ["RequestContextMiddleware"]
