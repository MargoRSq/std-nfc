import logging
from dataclasses import asdict

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from std_cards.core.exceptions import APIException, ValidationFailedError

logger = logging.getLogger(__name__)

SAFE_QUERY_KEYS = {
    "page",
    "limit",
    "offset",
    "sort",
    "order",
    "view",
    "from",
    "to",
    "q",
    "category",
}


def _safe_query(request: Request) -> dict[str, str]:
    return {k: v for k, v in request.query_params.items() if k.lower() in SAFE_QUERY_KEYS}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(APIException)
    async def _api_exception_handler(request: Request, exc: APIException) -> JSONResponse:
        content = exc.exception_response
        content.query = _safe_query(request)
        return JSONResponse(status_code=exc.STATUS_CODE, content=asdict(content))

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        logger.warning(
            "Request validation failed: path=%s errors=%s",
            request.url.path,
            exc.errors(),
        )
        wrapped = ValidationFailedError(
            message="Request validation failed",
            details={"errors": exc.errors()},
        )
        content = wrapped.exception_response
        content.query = _safe_query(request)
        return JSONResponse(status_code=wrapped.STATUS_CODE, content=asdict(content))

    @app.exception_handler(HTTPException)
    async def _http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        if isinstance(exc.detail, dict):
            details = exc.detail
            message = "HTTP error"
        else:
            details = {}
            message = "HTTP error"
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": "http_error",
                "message": message,
                "details": details,
                "query": _safe_query(request),
            },
        )

    @app.exception_handler(Exception)
    async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception", extra={"path": request.url.path})
        return JSONResponse(
            status_code=500,
            content={
                "code": "internal_error",
                "message": "Internal server error",
                "details": {},
                "query": _safe_query(request),
            },
        )
