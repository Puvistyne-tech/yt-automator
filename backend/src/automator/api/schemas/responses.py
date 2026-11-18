from __future__ import annotations

from typing import Any

from fastapi import Response, status
from pydantic import BaseModel, Field

CREATED = status.HTTP_201_CREATED
NO_CONTENT_RESPONSE: dict[str, Any] = {
    "status_code": status.HTTP_204_NO_CONTENT,
    "response_class": Response,
}


class HealthResponse(BaseModel):
    status: str = Field(description="ok when the API is serving")
    version: str = Field(description="Backend version")


class ConnectChannelResponse(BaseModel):
    authorization_url: str = Field(description="Google consent page to open")


class ErrorDetail(BaseModel):
    code: str
    message: str
    fields: dict[str, str] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    error: ErrorDetail


ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    status: {"model": ErrorResponse, "description": description}
    for status, description in (
        (400, "Validation failed"),
        (404, "Not found"),
        (409, "Rule conflict"),
        (502, "Upstream failure"),
        (500, "Unexpected server error"),
    )
}
