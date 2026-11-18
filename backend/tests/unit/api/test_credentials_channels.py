from __future__ import annotations

from collections.abc import Callable
from urllib.parse import parse_qs, urlparse

import pytest

from automator.domain.channels import channel_token_secret_name
from automator.domain.credentials import credential_secret_name
from automator.infrastructure.config import RuntimeConfig
from automator.main import Overrides
from tests.fixtures.fake_runtime import FakeClock, InMemorySecrets
from tests.fixtures.fake_youtube import FakeYouTube
from tests.unit.api.client import Api, error_of, ok, send, wired


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
    assert callback_error(api, code="c", state="") == "missing_code"
    assert callback_error(api, code="c", state="garbage") == "validation_failed"
    state = api.start_connect(api.credential()["id"])
    youtube.failing_operations.add("exchange_code")
    assert callback_error(api, code="c", state=state) == "upstream_failure"


def tampered(_api: Api, _clock: FakeClock, state: str) -> str:
    return state[:-1] + ("A" if state[-1] != "A" else "B")


def expired(_api: Api, clock: FakeClock, state: str) -> str:
    clock.advance(minutes=16)
    return state


def credential_deleted(api: Api, _clock: FakeClock, state: str) -> str:
    [credential] = ok(api.client.get("/api/credentials"))
    ok(api.client.delete(f"/api/credentials/{credential['id']}"), 204)
    return state


@pytest.mark.parametrize("spoil", [tampered, expired, credential_deleted])
def test_callback_rejects_spoiled_states(
    config: RuntimeConfig, overrides: Overrides, spoil: Callable[[Api, FakeClock, str], str]
) -> None:
    clock = FakeClock()
    with wired(config, overrides, clock=clock) as client:
        api = Api(client, client.app.state.runtime)  # type: ignore[attr-defined]
        state = spoil(api, clock, api.start_connect(api.credential()["id"]))
        assert callback_error(api, code="c", state=state) == "validation_failed"


def test_callback_redirects_to_the_configured_ui(
    config: RuntimeConfig, overrides: Overrides
) -> None:
    changed = config.model_copy(update={"ui_base_url": "http://ui:3000/"})
    with wired(changed, overrides) as client:
        response = client.get("/api/oauth/callback", params={"error": "access_denied"})
    assert response.headers["location"] == "http://ui:3000/channels?error=access_denied"


def test_patching_the_client_secret_rotates_it(api: Api, secrets: InMemorySecrets) -> None:
    created = api.credential()
    body = {"client_secret": "rotated"}
    patched = ok(api.client.patch(f"/api/credentials/{created['id']}", json=body))
    assert patched["has_secret"] is True and "rotated" not in str(patched)
    assert secrets.get(credential_secret_name(created["id"])) == "rotated"


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("patch", "/api/credentials/{credential}", {"name": ""}),
        ("patch", "/api/credentials/{credential}", {"daily_quota_units": -1}),
        ("patch", "/api/channels/{channel}", {"defaults": {"privacy": "nope"}}),
        ("post", "/api/channels/connect", {}),
    ],
)
def test_invalid_changes_to_real_records_are_rejected(
    api: Api, method: str, path: str, body: dict[str, object]
) -> None:
    credential = api.credential()
    channel = api.connect(credential["id"])
    target = path.format(credential=credential["id"], channel=channel)
    assert error_of(send(api.client, method, target, body), 400)["fields"]
