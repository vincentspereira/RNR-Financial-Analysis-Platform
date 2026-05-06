"""
Response compression middleware for reducing payload sizes.
"""
import gzip
import io
from typing import Dict, Tuple

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from app.core.config import settings
from app.core.logging import get_logger

compress_logger = get_logger("app.compression")

# Content types that benefit from compression
COMPRESSIBLE_TYPES = {
    "application/json",
    "text/html",
    "text/plain",
    "text/xml",
    "application/xml",
    "text/javascript",
    "application/javascript",
}


class CompressionMiddleware(BaseHTTPMiddleware):
    """Gzip response compression for API responses."""

    def __init__(self, app: ASGIApp, min_size: int = None, gzip_level: int = None):
        super().__init__(app)
        self.min_size = min_size or settings.COMPRESS_MIN_SIZE
        self.gzip_level = gzip_level or settings.COMPRESS_GZIP_LEVEL

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Skip if client doesn't accept gzip
        accept_encoding = request.headers.get("accept-encoding", "")
        if "gzip" not in accept_encoding:
            return await call_next(request)

        response = await call_next(request)

        # Check if response should be compressed
        content_type = response.headers.get("content-type", "")
        content_type_base = content_type.split(";")[0].strip().lower()

        if content_type_base not in COMPRESSIBLE_TYPES:
            return response

        # Read response body
        body = b""
        async for chunk in response.body_iterator:
            body += chunk

        # Skip small responses
        if len(body) < self.min_size:
            response.body_iterator = self._iter(body)
            return response

        # Compress
        compressed = gzip.compress(body, compresslevel=self.gzip_level)

        # Only use compressed version if it's actually smaller
        if len(compressed) >= len(body):
            response.body_iterator = self._iter(body)
            return response

        response.body_iterator = self._iter(compressed)
        response.headers["content-encoding"] = "gzip"
        response.headers["content-length"] = str(len(compressed))
        response.headers["vary"] = "Accept-Encoding"

        return response

    @staticmethod
    async def _iter(body: bytes):
        yield body
