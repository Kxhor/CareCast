"""FastAPI application factory, security middleware, and error handlers (Phase 4).

Hardened per:
- TRD §9.2: Security headers, zero CORS, zero cookies
- TRD §9.1: Body size limit (8 KB)
- BACKEND_SCHEMA §7.1: Generic error envelopes with server-side request IDs
- TRD §8: Docs enabled only when CARECAST_ENV=dev and CARECAST_ENABLE_DOCS=1
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any, Callable

from fastapi import FastAPI, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from carecast.api.ratelimit import SlidingWindowRateLimiter
from carecast.api.routes import router
from carecast.settings import Settings, get_settings

logger = logging.getLogger("carecast.api")

CSP_POLICY = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self'; "
    "img-src 'self' data:; "
    "connect-src 'self'; "
    "font-src 'self'; "
    "object-src 'none'; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "frame-ancestors 'none'"
)

MAX_BODY_BYTES = 8192  # 8 KB


class SecurityAndHardeningMiddleware(BaseHTTPMiddleware):
    """Unified HTTP hardening middleware:
    - Generates and attaches X-Request-ID
    - Enforces 8 KB body size limit on POST
    - Applies in-memory rate limiting
    - Injects security response headers (CSP, HSTS, frame-ancestors, etc.)
    - Strips CORS and cookie headers
    """

    def __init__(self, app: Any, settings: Settings, rate_limiter: SlidingWindowRateLimiter) -> None:
        super().__init__(app)
        self.settings = settings
        self.rate_limiter = rate_limiter

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 1. Server-side Request ID
        req_id = str(uuid.uuid4())
        request.state.request_id = req_id

        # 2. Body size limit (8 KB cap) for POST requests
        if request.method == "POST":
            content_length = request.headers.get("content-length")
            if content_length and content_length.isdigit() and int(content_length) > MAX_BODY_BYTES:
                return self._create_error_response(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    code="payload_too_large",
                    message=f"Request body exceeds maximum size of {MAX_BODY_BYTES} bytes.",
                    fields=[],
                    req_id=req_id,
                )

            # Stream inspection in case Content-Length was omitted
            body = await request.body()
            if len(body) > MAX_BODY_BYTES:
                return self._create_error_response(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    code="payload_too_large",
                    message=f"Request body exceeds maximum size of {MAX_BODY_BYTES} bytes.",
                    fields=[],
                    req_id=req_id,
                )

        # 3. Rate limiting on /api/* routes
        path = request.url.path
        if path.startswith("/api/"):
            client_ip = self._get_client_ip(request)
            max_reqs = (
                self.settings.rate_post_per_min
                if request.method == "POST"
                else self.settings.rate_get_per_min
            )
            key = f"{client_ip}:{request.method}"
            allowed, retry_after = self.rate_limiter.is_allowed(key, max_reqs)
            if not allowed:
                headers = {"Retry-After": str(retry_after)}
                return self._create_error_response(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    code="rate_limited",
                    message="Rate limit exceeded. Please retry later.",
                    fields=[],
                    req_id=req_id,
                    extra_headers=headers,
                )

        # 4. Call handler
        response = await call_next(request)

        # 5. Inject security headers
        response.headers["X-Request-ID"] = req_id
        response.headers["Content-Security-Policy"] = CSP_POLICY
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"

        if path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"

        if self.settings.hsts:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

        # 6. Strict absence of CORS and Cookie headers
        for h in list(response.headers.keys()):
            h_lower = h.lower()
            if h_lower.startswith("access-control-") or h_lower == "set-cookie":
                del response.headers[h]

        return response

    def _get_client_ip(self, request: Request) -> str:
        if self.settings.trusted_proxy:
            xff = request.headers.get("x-forwarded-for")
            if xff:
                return xff.split(",")[0].strip()
        if request.client and request.client.host:
            return request.client.host
        return "127.0.0.1"

    def _create_error_response(
        self,
        status_code: int,
        code: str,
        message: str,
        fields: list[str],
        req_id: str,
        extra_headers: dict[str, str] | None = None,
    ) -> JSONResponse:
        headers = {
            "X-Request-ID": req_id,
            "Content-Security-Policy": CSP_POLICY,
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer",
            "X-Frame-Options": "DENY",
            "Permissions-Policy": "geolocation=(), camera=(), microphone=()",
            "Cache-Control": "no-store",
        }
        if self.settings.hsts:
            headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        if extra_headers:
            headers.update(extra_headers)

        content = {
            "error": {
                "code": code,
                "message": message,
                "fields": fields,
                "request_id": req_id,
            }
        }
        return JSONResponse(status_code=status_code, content=content, headers=headers)


def create_app(settings: Settings | None = None) -> FastAPI:
    """FastAPI application factory."""
    if settings is None:
        settings = get_settings()

    # Docs URLs disabled unless dev environment with docs explicitly enabled
    docs_url = "/docs" if settings.enable_docs else None
    redoc_url = "/redoc" if settings.enable_docs else None
    openapi_url = "/openapi.json" if settings.enable_docs else None

    app = FastAPI(
        title="CareCast",
        version="0.1.0",
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
    )

    app.state.settings = settings
    rate_limiter = SlidingWindowRateLimiter(window_seconds=60.0)
    app.state.rate_limiter = rate_limiter

    # Register hardening middleware
    app.add_middleware(
        SecurityAndHardeningMiddleware,
        settings=settings,
        rate_limiter=rate_limiter,
    )

    # Error Handlers
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        req_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        # Extract field names only (never echo input values)
        fields: list[str] = []
        for error in exc.errors():
            loc = error.get("loc", ())
            if loc:
                field_name = str(loc[-1])
                if field_name not in fields:
                    fields.append(field_name)

        content = {
            "error": {
                "code": "validation_error",
                "message": "One or more inputs are invalid.",
                "fields": fields,
                "request_id": req_id,
            }
        }
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=content,
            headers={"X-Request-ID": req_id, "Cache-Control": "no-store"},
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        req_id = getattr(request.state, "request_id", str(uuid.uuid4()))

        code = "error"
        message = "An error occurred."
        fields: list[str] = []

        if isinstance(exc.detail, dict):
            code = exc.detail.get("code", "error")
            message = exc.detail.get("message", "An error occurred.")
            fields = exc.detail.get("fields", [])
        else:
            message = str(exc.detail)
            if exc.status_code == status.HTTP_404_NOT_FOUND:
                code = "series_unavailable"
            elif exc.status_code == status.HTTP_405_METHOD_NOT_ALLOWED:
                code = "method_not_allowed"
            elif exc.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE:
                code = "payload_too_large"
            elif exc.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
                code = "validation_error"
            elif exc.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
                code = "rate_limited"
            elif exc.status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
                code = "data_unavailable"
            elif exc.status_code >= 500:
                code = "internal_error"

        content = {
            "error": {
                "code": code,
                "message": message,
                "fields": fields,
                "request_id": req_id,
            }
        }
        return JSONResponse(
            status_code=exc.status_code,
            content=content,
            headers={"X-Request-ID": req_id, "Cache-Control": "no-store"},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        req_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        logger.error("Unhandled server exception [req_id=%s]: %s", req_id, exc, exc_info=True)

        content = {
            "error": {
                "code": "internal_error",
                "message": "An internal server error occurred.",
                "fields": [],
                "request_id": req_id,
            }
        }
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=content,
            headers={"X-Request-ID": req_id, "Cache-Control": "no-store"},
        )

    # Mount API router
    app.include_router(router)

    # Static mount for web/ placeholder
    web_dir = Path("web")
    if web_dir.exists():
        app.mount("/", StaticFiles(directory=str(web_dir), html=True), name="web")

    return app
