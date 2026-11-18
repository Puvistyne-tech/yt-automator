from __future__ import annotations

from collections.abc import Callable
from urllib.parse import parse_qs, urlparse

import pytest

from automator.application.delete_channel import DeleteChannel
from automator.application.list_channel_playlists import ListChannelPlaylists
from automator.application.list_channels import ListChannels
from automator.application.update_channel_defaults import UpdateChannelDefaults
from automator.domain.automations import Automation
from automator.domain.channels import (
    Channel,
    ChannelDefaults,
    ChannelStatus,
    Privacy,
    channel_token_secret_name,
)
from automator.domain.credentials import Credential, credential_secret_name
from automator.domain.youtube import ChannelProfile
from automator.shared.errors import NotFound, RuleConflict, ValidationFailed
from tests.fixtures.builders import add_channel, add_credential
from tests.fixtures.harness import Harness
from tests.fixtures.use_cases import complete_connect, start_connect


def connect_url_state(harness: Harness, credential_id: str = "cred-1") -> str:
    started = start_connect(harness).execute(credential_id)
    query = parse_qs(urlparse(started.authorization_url).query)
    assert query["state"] == [started.state]
    assert query["client_id"] == [f"client-{credential_id}"]
    return started.state


def test_connect_flow_creates_channel_and_stores_token(
    harness: Harness, credential: Credential
) -> None:
    state = connect_url_state(harness)
    channel = complete_connect(harness).execute("code-9", state)
    assert harness.channels.get(channel.id) == channel
    assert (channel.youtube_channel_id, channel.status) == ("UC-fake", ChannelStatus.CONNECTED)
    assert channel.credential_id == credential.id
    token = harness.secrets.get(channel_token_secret_name(channel.id))
    assert token == "token-for-code-9-client-cred-1"
    assert harness.youtube.operations("describe_channel") == [token]


@pytest.mark.usefixtures("credential")
def test_reconnect_updates_existing_channel_and_keeps_defaults(harness: Harness) -> None:
    existing = add_channel(harness, defaults=ChannelDefaults(privacy=Privacy.PUBLIC))
    harness.youtube.profile = ChannelProfile(
        youtube_channel_id=existing.youtube_channel_id, title="New"
    )
    harness.clock.advance(minutes=1)
    channel = complete_connect(harness).execute("code", connect_url_state(harness))
    assert channel.id == existing.id and channel.title == "New"
    assert channel.defaults.privacy is Privacy.PUBLIC
    assert channel.connected_at == harness.clock.now()
    assert len(harness.channels.list()) == 1


def expire(harness: Harness, state: str) -> str:
    harness.clock.advance(minutes=16)
    return state


def tamper(_harness: Harness, state: str) -> str:
    return state[:-2] + ("00" if not state.endswith("00") else "11")


def forget_credential(harness: Harness, state: str) -> str:
    harness.credentials.delete("cred-1")
    return state


def garble(_harness: Harness, _state: str) -> str:
    return "garbage"


@pytest.mark.parametrize(
    ("mutate", "reason"),
    [
        (expire, "expired"),
        (tamper, "signature mismatch"),
        (forget_credential, "unknown credential"),
        (garble, "malformed"),
    ],
)
@pytest.mark.usefixtures("credential")
def test_complete_connect_rejects_bad_state(
    harness: Harness, mutate: Callable[[Harness, str], str], reason: str
) -> None:
    state = mutate(harness, connect_url_state(harness))
    with pytest.raises(ValidationFailed) as raised:
        complete_connect(harness).execute("code", state)
    assert raised.value.fields == {"state": reason}
    assert harness.channels.list() == []


def test_start_connect_requires_credential_and_secret(harness: Harness) -> None:
    with pytest.raises(NotFound):
        start_connect(harness).execute("missing")
    add_credential(harness, secret=None)
    with pytest.raises(RuleConflict) as raised:
        start_connect(harness).execute("cred-1")
    assert raised.value.code == "credential_secret_missing"


def test_rotated_client_secret_invalidates_pending_state(
    harness: Harness, credential: Credential
) -> None:
    state = connect_url_state(harness)
    harness.secrets.set(credential_secret_name(credential.id), "rotated")
    harness.clock.advance(minutes=1)
    with pytest.raises(ValidationFailed):
        complete_connect(harness).execute("code", state)


def test_update_defaults(harness: Harness, channel: Channel) -> None:
    defaults = ChannelDefaults(privacy=Privacy.UNLISTED, made_for_kids=True, category_id="1")
    updated = UpdateChannelDefaults(harness.channels).execute(channel.id, defaults)
    assert harness.channels.get(channel.id) == updated and updated.defaults == defaults
    with pytest.raises(NotFound):
        UpdateChannelDefaults(harness.channels).execute("nope", defaults)


def delete(harness: Harness) -> DeleteChannel:
    return DeleteChannel(harness.channels, harness.automations, harness.secrets)


def test_delete_refused_while_enabled_automation_targets_it(
    harness: Harness, automation: Automation
) -> None:
    with pytest.raises(RuleConflict) as raised:
        delete(harness).execute("chan-1")
    assert raised.value.code == "channel_in_use"
    harness.automations.save(automation.model_copy(update={"enabled": False}))
    delete(harness).execute("chan-1")
    assert harness.channels.get("chan-1") is None
    assert not harness.secrets.has(channel_token_secret_name("chan-1"))


def test_delete_unknown_channel(harness: Harness) -> None:
    with pytest.raises(NotFound):
        delete(harness).execute("nope")


@pytest.mark.usefixtures("credential")
def test_list_channels_sorted_by_title(harness: Harness) -> None:
    add_channel(harness, channel_id="b")
    add_channel(harness, channel_id="a")
    assert [c.id for c in ListChannels(harness.channels).execute()] == ["a", "b"]


def playlists(harness: Harness) -> ListChannelPlaylists:
    return ListChannelPlaylists(harness.channels, harness.authorizer, harness.youtube)


def test_list_playlists_uses_channel_token(harness: Harness, channel: Channel) -> None:
    assert [p.id for p in playlists(harness).execute(channel.id)] == ["PL-1"]
    assert harness.youtube.tokens == ["tok"]


@pytest.mark.usefixtures("credential")
def test_list_playlists_without_token_is_a_conflict(harness: Harness) -> None:
    add_channel(harness, token=None)
    with pytest.raises(RuleConflict) as raised:
        playlists(harness).execute("chan-1")
    assert raised.value.code == "channel_not_authorized"
    with pytest.raises(NotFound):
        playlists(harness).execute("ghost")
