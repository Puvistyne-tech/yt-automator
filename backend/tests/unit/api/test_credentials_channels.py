from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pytest

from automator.domain.channels import channel_token_secret_name
from tests.fixtures.fake_runtime import InMemorySecrets
from tests.fixtures.fake_youtube import FakeYouTube
from tests.unit.api.client import Api, error_of, ok, send


def test_credentials_crud_never_returns_the_secret(api: Api, secrets: InMemorySecrets) -> None:
    client = api.client
    created = api.credential()
    assert set(created) == {
        "id",
        "name",
        "client_id",
        "daily_quota_units",
        "created_at",
        "has_secret",
        "quota_used_today",
    }
    assert (created["daily_quota_units"], created["has_secret"]) == (10000, True)
    patched = ok(client.patch(f"/api/credentials/{created['id']}", json={"name": "Renamed"}))
    assert (patched["name"], patched["quota_used_today"]) == ("Renamed", 0)
    [listed] = ok(client.get("/api/credentials"))
    assert (listed["has_secret"], listed["quota_used_today"]) == (True, 0)
    assert "csecret" not in client.get("/api/credentials").text
    assert ok(client.delete(f"/api/credentials/{created['id']}"), 204) is None
    assert ok(client.get("/api/credentials")) == []
    assert secrets.values == {}


@pytest.mark.parametrize(
    ("method", "path", "body", "status"),
    [
        ("post", "/api/credentials", {"name": "", "client_id": "c", "client_secret": "s"}, 400),
        ("post", "/api/credentials", {"name": "n", "client_id": "c"}, 400),
        ("patch", "/api/credentials/missing", {"name": "x"}, 404),
        ("delete", "/api/credentials/missing", None, 404),
        ("post", "/api/channels/connect", {"credential_id": "missing"}, 404),
        ("patch", "/api/channels/missing", {"defaults": {}}, 404),
        ("delete", "/api/channels/missing", None, 404),
        ("get", "/api/channels/missing/playlists", None, 404),
    ],
)
def test_credential_and_channel_errors(
    api: Api, method: str, path: str, body: object, status: int
) -> None:
    error_of(send(api.client, method, path, body), status)


def test_channel_lifecycle(api: Api, secrets: InMemorySecrets) -> None:
    client = api.client
    credential = api.credential()
    channel_id = api.connect(credential["id"])
    assert secrets.get(channel_token_secret_name(channel_id)) == "token-for-c0de-cid"
    error_of(client.delete(f"/api/credentials/{credential['id']}"), 409)
    defaults = {"privacy": "unlisted", "made_for_kids": True, "category_id": "27"}
    patched = ok(client.patch(f"/api/channels/{channel_id}", json={"defaults": defaults}))
    assert patched["defaults"]["privacy"] == "unlisted"
    assert patched["defaults"]["default_language"] == "en"
    playlists = ok(client.get(f"/api/channels/{channel_id}/playlists"))
    assert playlists == [{"id": "PL-1", "title": "Stories"}]
    api.automation(channel_id)
    error_of(client.delete(f"/api/channels/{channel_id}"), 409)


def test_disconnect_after_disabling_the_automation(api: Api) -> None:
    channel_id = api.channel()
    automation = api.automation(channel_id, enabled=False)
    assert automation["enabled"] is False
    ok(api.client.delete(f"/api/channels/{channel_id}"), 204)
    assert ok(api.client.get("/api/channels")) == []


def test_playlist_failure_is_a_bad_gateway(api: Api, youtube: FakeYouTube) -> None:
    channel_id = api.channel()
    youtube.failing_operations.add("list_playlists")
    assert error_of(api.client.get(f"/api/channels/{channel_id}/playlists"), 502)["message"]


def callback_error(api: Api, **params: str) -> str:
    response = api.client.get("/api/oauth/callback", params=params)
    assert response.status_code == 303
    return parse_qs(urlparse(response.headers["location"]).query)["error"][0]


def test_callback_redirects_with_error_codes(api: Api, youtube: FakeYouTube) -> None:
    assert callback_error(api, error="access_denied", state="s") == "access_denied"
    assert callback_error(api, state="s") == "missing_code"
    assert callback_error(api, code="c", state="garbage") == "validation_failed"
    credential = api.credential()
    started = ok(api.client.post("/api/channels/connect", json={"credential_id": credential["id"]}))
    state = parse_qs(urlparse(started["authorization_url"]).query)["state"][0]
    youtube.failing_operations.add("exchange_code")
    assert callback_error(api, code="c", state=state) == "upstream_failure"
