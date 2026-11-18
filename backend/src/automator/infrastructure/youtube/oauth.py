from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow  # type: ignore[import-untyped]
from oauthlib.oauth2.rfc6749.errors import OAuth2Error

from automator.domain.youtube import ChannelAuth, OAuthClient
from automator.infrastructure.youtube.errors import google_errors
from automator.infrastructure.youtube.settings import YouTubeSettings
from automator.shared.errors import UpstreamFailure

TOKEN_FIELDS = ("token", "refresh_token", "token_uri", "scopes", "expiry")
FlowFactory = Callable[[OAuthClient, YouTubeSettings], Any]
Refresher = Callable[[Credentials], None]


def client_config(client: OAuthClient, settings: YouTubeSettings) -> dict[str, Any]:
    return {
        "web": {
            "client_id": client.client_id,
            "client_secret": client.client_secret,
            "auth_uri": settings.auth_uri,
            "token_uri": settings.token_uri,
            "redirect_uris": [settings.redirect_uri],
        }
    }


def google_flow(client: OAuthClient, settings: YouTubeSettings) -> Any:
    return Flow.from_client_config(
        client_config(client, settings),
        scopes=list(settings.scopes),
        redirect_uri=settings.redirect_uri,
        autogenerate_code_verifier=False,
    )


def token_blob(credentials: Credentials) -> str:
    info = json.loads(credentials.to_json())  # type: ignore[no-untyped-call]
    return json.dumps({key: info[key] for key in TOKEN_FIELDS if key in info}, sort_keys=True)


def oauth_failure(error: OAuth2Error) -> UpstreamFailure:
    code = "youtube_invalid_grant" if error.error == "invalid_grant" else "youtube_oauth_failed"
    return UpstreamFailure(f"Google rejected the authorization: {error.error}", code)


def refresh_with_google(credentials: Credentials) -> None:
    credentials.refresh(Request())  # type: ignore[no-untyped-call]


def load_credentials(auth: ChannelAuth, refresher: Refresher) -> Credentials:
    client = {"client_id": auth.client.client_id, "client_secret": auth.client.client_secret}
    try:
        info = json.loads(auth.token) | client
        credentials: Credentials = Credentials.from_authorized_user_info(info)  # type: ignore[no-untyped-call]
    except (ValueError, TypeError) as error:
        raise UpstreamFailure("stored token is unreadable", "youtube_token_invalid") from error
    if not credentials.valid:
        with google_errors():
            refresher(credentials)
    return credentials


class GoogleOAuth:
    def __init__(self, settings: YouTubeSettings, flows: FlowFactory = google_flow) -> None:
        self.settings = settings
        self.flows = flows

    def authorization_url(self, client: OAuthClient, state: str) -> str:
        flow = self.flows(client, self.settings)
        url, _ = flow.authorization_url(access_type="offline", prompt="consent", state=state)
        return str(url)

    def exchange_code(self, client: OAuthClient, code: str) -> str:
        flow = self.flows(client, self.settings)
        try:
            with google_errors():
                flow.fetch_token(code=code)
        except OAuth2Error as error:
            raise oauth_failure(error) from error
        return token_blob(flow.credentials)
