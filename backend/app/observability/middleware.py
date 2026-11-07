import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = structlog.get_logger()


class RequestTracingMiddleware(BaseHTTPMiddleware):
    """Adds a trace_id to every request for log correlation."""

    async def dispatch(self, request: Request, call_next):
        trace_id = request.headers.get("X-Trace-Id", str(uuid.uuid4())[:8])
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            trace_id=trace_id,
            method=request.method,
            path=request.url.path,
        )

        start = time.monotonic()
        response = await call_next(request)
        elapsed_ms = (time.monotonic() - start) * 1000

        logger.info(
            "request_completed",
            status_code=response.status_code,
            latency_ms=round(elapsed_ms, 2),
        )
        response.headers["X-Trace-Id"] = trace_id
        return response
