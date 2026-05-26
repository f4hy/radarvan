import time
import uuid

import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

logger = structlog.get_logger(__name__)

REQUEST_ID_HEADER = "X-Request-ID"
CLIENT_ID_HEADER = "X-Client-Id"


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Assign a request id, identify the caller, and log timing per request.

    Reuses an incoming X-Request-ID if the caller supplied one, otherwise
    generates a uuid4. The id and caller are bound to structlog's contextvars
    so every log line emitted while handling the request carries them, and the
    id is echoed back in the response headers. Callers identify themselves via
    X-Client-Id (the React app sends "react-frontend").
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        client_id = request.headers.get(CLIENT_ID_HEADER, "unknown")
        # Stored on state so the app-level exception handler can echo the id
        # back on the 500 path, where call_next raises past this point.
        request.state.request_id = request_id
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id, client=client_id)

        start_time = time.time()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers[REQUEST_ID_HEADER] = request_id
            return response
        finally:
            logger.info(
                "request",
                method=request.method,
                path=request.url.path,
                status=status,
                took=round(time.time() - start_time, 4),
            )
            structlog.contextvars.clear_contextvars()
