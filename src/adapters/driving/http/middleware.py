"""HTTP middleware for the FleetFlow API."""

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log method, path, status code, and duration for every HTTP request."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Log request completion and re-raise unhandled failures.

        Args:
            request: Incoming HTTP request.
            call_next: Next middleware or endpoint handler.

        Returns:
            HTTP response from the downstream handler.

        Raises:
            Exception: Re-raises unhandled downstream failures after logging them.
        """
        start = time.monotonic()

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.monotonic() - start) * 1000
            logger.exception(
                "%s %s -> unhandled error (%.1fms)",
                request.method,
                request.url.path,
                duration_ms,
            )
            raise

        duration_ms = (time.monotonic() - start) * 1000
        logger.info(
            "%s %s -> %d (%.1fms)",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response
