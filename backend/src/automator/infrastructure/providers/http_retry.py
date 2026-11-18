from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

import httpx
from pydantic import Field

from automator.infrastructure.providers.context import ProviderContext
from automator.infrastructure.providers.json_response import json_body
from automator.infrastructure.providers.spec import ProviderOptions
from automator.shared.errors import UpstreamFailure


class HttpOptions(ProviderOptions):
    timeout_seconds: float = Field(
        default=120.0, gt=0, title="Timeout", description="Seconds to wait for one HTTP response."
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        title="Retries",
        description="Extra attempts after a rate limit (429), server error (5xx) or network error.",
    )
    backoff_seconds: float = Field(
        default=2.0,
        ge=0,
        title="Backoff",
        description="Wait before the first retry; doubles on every further retry.",
    )


def is_retryable(status: int) -> bool:
    return status == 429 or status >= 500


def retry_after(response: httpx.Response) -> float:
    try:
        return float(response.headers.get("retry-after", "0"))
    except ValueError:
        return 0.0


def failure(label: str, response: httpx.Response) -> UpstreamFailure:
    return UpstreamFailure(f"{label} returned HTTP {response.status_code}: {response.text[-500:]}")


def attempt(send: Callable[[], httpx.Response], label: str) -> httpx.Response | str:
    try:
        return send()
    except httpx.HTTPError as error:
        return f"{label} request failed: {type(error).__name__}: {error}"


def send_with_retry(
    send: Callable[[], httpx.Response],
    options: HttpOptions,
    sleep: Callable[[float], None],
    label: str,
) -> httpx.Response:
    last = f"{label} was not called"
    for index in range(options.max_retries + 1):
        outcome = attempt(send, label)
        wait = options.backoff_seconds * 2**index
        if isinstance(outcome, httpx.Response):
            if not is_retryable(outcome.status_code):
                return outcome
            last = failure(label, outcome).message
            wait = max(wait, retry_after(outcome))
        else:
            last = outcome
        if index < options.max_retries:
            sleep(wait)
    raise UpstreamFailure(last)


def post_json(
    client: httpx.Client,
    url: str,
    payload: Mapping[str, Any],
    headers: Mapping[str, str],
    options: HttpOptions,
    sleep: Callable[[float], None],
    label: str,
) -> dict[str, Any]:
    with client:
        response = send_with_retry(
            lambda: client.post(url, json=dict(payload), headers=dict(headers)),
            options,
            sleep,
            label,
        )
        if response.is_error:
            raise failure(label, response)
        return json_body(response, label)


def post_provider_json(
    context: ProviderContext,
    options: HttpOptions,
    base_url: str,
    path: str,
    payload: Mapping[str, Any],
    headers: Mapping[str, str],
    label: str,
) -> dict[str, Any]:
    url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
    client = context.http(options.timeout_seconds)
    return post_json(client, url, payload, headers, options, context.sleep, label)
