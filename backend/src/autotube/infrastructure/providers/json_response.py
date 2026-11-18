from __future__ import annotations

from typing import Any

import httpx

from autotube.shared.errors import UpstreamFailure


def json_body(response: httpx.Response, label: str) -> dict[str, Any]:
    try:
        body = response.json()
    except ValueError as error:
        raise UpstreamFailure(f"{label} returned invalid JSON") from error
    if not isinstance(body, dict):
        raise UpstreamFailure(f"{label} returned an unexpected JSON shape")
    return body


def dig(body: Any, label: str, *path: str | int) -> Any:
    current = body
    try:
        for key in path:
            current = current[key]
    except (KeyError, IndexError, TypeError) as error:
        raise UpstreamFailure(f"{label} response is missing {path!r}") from error
    return current
