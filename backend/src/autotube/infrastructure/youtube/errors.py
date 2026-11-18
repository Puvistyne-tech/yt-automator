from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import httplib2  # type: ignore[import-untyped]
from google.auth.exceptions import RefreshError, TransportError
from googleapiclient.errors import HttpError  # type: ignore[import-untyped]

from autotube.domain.youtube import AUTHORIZATION_EXPIRED_CODE
from autotube.shared.errors import UpstreamFailure

QUOTA_REASONS = frozenset({"quotaExceeded", "dailyLimitExceeded", "rateLimitExceeded"})
STATUS_CODES = {
    400: "youtube_bad_request",
    401: "youtube_unauthorized",
    403: "youtube_forbidden",
    404: "youtube_not_found",
}


def error_reasons(error: Any) -> set[str]:
    try:
        body = json.loads(error.content)
    except (TypeError, ValueError):
        return set()
    details = body.get("error", {}).get("errors", []) if isinstance(body, dict) else []
    return {str(item.get("reason", "")) for item in details if isinstance(item, dict)}


def http_failure(error: Any) -> UpstreamFailure:
    status = int(getattr(error.resp, "status", 0) or 0)
    reasons = error_reasons(error)
    message = f"YouTube returned {status}: {getattr(error, 'reason', '') or 'request failed'}"
    if reasons & QUOTA_REASONS:
        return UpstreamFailure(f"YouTube quota exceeded ({status})", "youtube_quota_exceeded")
    return UpstreamFailure(message, STATUS_CODES.get(status, "youtube_error"))


def refresh_failure(error: RefreshError) -> UpstreamFailure:
    if "invalid_grant" in str(error):
        return UpstreamFailure(
            "the channel authorization was revoked or expired; reconnect the channel",
            AUTHORIZATION_EXPIRED_CODE,
        )
    return UpstreamFailure("could not refresh the channel authorization", "youtube_auth_failed")


@contextmanager
def google_errors() -> Iterator[None]:
    try:
        yield
    except HttpError as error:
        raise http_failure(error) from error
    except RefreshError as error:
        raise refresh_failure(error) from error
    except (TransportError, OSError, httplib2.HttpLib2Error) as error:
        raise unreachable() from error


def unreachable() -> UpstreamFailure:
    return UpstreamFailure("could not reach Google", "youtube_unreachable")
