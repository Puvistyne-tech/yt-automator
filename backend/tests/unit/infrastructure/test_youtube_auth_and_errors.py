from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import parse_qs, urlparse

import httplib2  # type: ignore[import-untyped]
import pytest
from google.auth.exceptions import RefreshError, TransportError
from google.oauth2.credentials import Credentials
from googleapiclient.errors import HttpError  # type: ignore[import-untyped]
from oauthlib.oauth2.rfc6749.errors import InvalidGrantError

from automator.infrastructure.youtube.errors import google_errors
from automator.infrastructure.youtube.gateway import GoogleYouTubeGateway
from automator.infrastructure.youtube.oauth import GoogleOAuth
from automator.infrastructure.youtube.settings import YouTubeSettings
from automator.shared.errors import UpstreamFailure
from tests.unit.infrastructure.youtube_fakes import CLIENT, FakeService, auth

REDIRECT = "http://127.0.0.1:9000/api/oauth/callback"


def http_error(status: int, reason: str = "") -> HttpError:
    body = {"error": {"errors": [{"reason": reason}], "message": "nope"}}
    return HttpError(httplib2.Response({"status": status}), json.dumps(body).encode())


@dataclass
class FakeFlow:
    failure: Exception | None = None
    codes: list[str] = field(default_factory=list)
    credentials: Credentials = field(
        default_factory=lambda: Credentials(  # type: ignore[no-untyped-call]
            token="at",
            refresh_token="rt",
            token_uri="https://oauth2.googleapis.com/token",
            client_id="cid",
            client_secret="csecret",
            scopes=["s"],
        )
    )

    def fetch_token(self, code: str) -> None:
        self.codes.append(code)
        if self.failure is not None:
            raise self.failure


def test_authorization_url_asks_for_offline_consent() -> None:
    gateway = GoogleYouTubeGateway(YouTubeSettings(redirect_uri=REDIRECT))
    url = urlparse(gateway.authorization_url(CLIENT, "signed-state"))
    query = {key: values[0] for key, values in parse_qs(url.query).items()}
    assert (url.netloc, query["client_id"], query["state"]) == (
        "accounts.google.com",
        "cid",
        "signed-state",
    )
    assert (query["access_type"], query["prompt"], query["redirect_uri"]) == (
        "offline",
        "consent",
        REDIRECT,
    )
    assert set(query["scope"].split()) == set(YouTubeSettings().scopes)
    assert "code_challenge" not in query


def test_exchange_returns_a_token_blob_without_the_client_secret() -> None:
    flow = FakeFlow()
    oauth = GoogleOAuth(YouTubeSettings(), flows=lambda _client, _settings: flow)
    blob = json.loads(oauth.exchange_code(CLIENT, "the-code"))
    assert flow.codes == ["the-code"]
    assert (blob["token"], blob["refresh_token"]) == ("at", "rt")
    assert "client_secret" not in blob


def test_exchange_translates_a_rejected_code() -> None:
    flow = FakeFlow(failure=InvalidGrantError())
    oauth = GoogleOAuth(YouTubeSettings(), flows=lambda _client, _settings: flow)
    with pytest.raises(UpstreamFailure) as raised:
        oauth.exchange_code(CLIENT, "bad")
    assert raised.value.code == "youtube_invalid_grant"


@pytest.mark.parametrize(
    ("error", "code"),
    [
        (http_error(403, "quotaExceeded"), "youtube_quota_exceeded"),
        (http_error(403, "forbidden"), "youtube_forbidden"),
        (http_error(401), "youtube_unauthorized"),
        (http_error(404, "videoNotFound"), "youtube_not_found"),
        (http_error(500, "backendError"), "youtube_error"),
        (RefreshError("invalid_grant: revoked"), "youtube_invalid_grant"),  # type: ignore[no-untyped-call]
        (RefreshError("other"), "youtube_auth_failed"),  # type: ignore[no-untyped-call]
        (TransportError("dns"), "youtube_unreachable"),  # type: ignore[no-untyped-call]
    ],
)
def test_google_errors_become_upstream_failures(error: Exception, code: str) -> None:
    with pytest.raises(UpstreamFailure) as raised, google_errors():
        raise error
    assert raised.value.code == code


def test_gateway_calls_translate_errors() -> None:
    service = FakeService()
    service.respond("playlistItems", "insert", http_error(403, "quotaExceeded"))
    gateway = GoogleYouTubeGateway(YouTubeSettings(), services=lambda _c: service, media=dict)
    with pytest.raises(UpstreamFailure) as raised:
        gateway.add_to_playlist(auth(), "v", "p")
    assert raised.value.code == "youtube_quota_exceeded"


def test_refresh_failure_is_translated() -> None:
    def refuse(_credentials: Any) -> None:
        raise RefreshError("invalid_grant")  # type: ignore[no-untyped-call]

    service = FakeService()
    gateway = GoogleYouTubeGateway(
        YouTubeSettings(), services=lambda _c: service, media=dict, refresher=refuse
    )
    expired = auth({"token": "at", "refresh_token": "rt", "expiry": "2000-01-01T00:00:00Z"})
    with pytest.raises(UpstreamFailure) as raised:
        gateway.list_playlists(expired)
    assert raised.value.code == "youtube_invalid_grant"
