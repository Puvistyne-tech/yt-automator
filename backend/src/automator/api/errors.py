from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from automator.domain.validation import ROOT_FIELD, field_path
from automator.shared.errors import (
    AppError,
    NotFound,
    RuleConflict,
    UpstreamFailure,
    ValidationFailed,
)

logger = logging.getLogger(__name__)

LOCATION_KINDS = frozenset({"body", "query", "path", "header", "cookie"})
ERROR_STATUS: tuple[tuple[type[AppError], int], ...] = (
    (NotFound, 404),
    (ValidationFailed, 400),
    (RuleConflict, 409),
    (UpstreamFailure, 502),
)
HTTP_ERROR_CODES = {404: "not_found", 405: "method_not_allowed"}


def error_body(code: str, message: str, fields: Mapping[str, str] | None = None) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "fields": dict(fields or {})}}


def status_for(error: AppError) -> int:
    return next((status for kind, status in ERROR_STATUS if isinstance(error, kind)), 400)


def location_path(location: Sequence[Any]) -> str:
    parts = list(location)
    if parts and parts[0] in LOCATION_KINDS:
        parts = parts[1:]
    return field_path(*parts) or ROOT_FIELD


def validation_fields(error: RequestValidationError) -> dict[str, str]:
    fields: dict[str, str] = {}
    for detail in error.errors():
        fields.setdefault(location_path(detail.get("loc", ())), str(detail.get("msg", "")))
    return fields


async def app_error_handler(_: Request, error: Exception) -> JSONResponse:
    assert isinstance(error, AppError)
    body = error_body(error.code, error.message, error.fields)
    return JSONResponse(body, status_code=status_for(error))


async def request_validation_handler(_: Request, error: Exception) -> JSONResponse:
    assert isinstance(error, RequestValidationError)
    body = error_body("validation_failed", "Validation failed", validation_fields(error))
    return JSONResponse(body, status_code=400)


async def http_error_handler(_: Request, error: Exception) -> JSONResponse:
    assert isinstance(error, HTTPException)
    code = HTTP_ERROR_CODES.get(error.status_code, f"http_{error.status_code}")
    body = error_body(code, str(error.detail))
    return JSONResponse(body, status_code=error.status_code, headers=error.headers)


async def unexpected_error_handler(_: Request, error: Exception) -> JSONResponse:
    logger.error("unexpected %s while serving a request", type(error).__name__)
    body = error_body("internal_error", "Unexpected server error")
    return JSONResponse(body, status_code=500)


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, request_validation_handler)
    app.add_exception_handler(HTTPException, http_error_handler)
    app.add_exception_handler(Exception, unexpected_error_handler)
