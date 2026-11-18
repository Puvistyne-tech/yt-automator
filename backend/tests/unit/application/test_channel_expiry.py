from __future__ import annotations

import pytest

from automator.domain.channels import Channel, ChannelStatus
from automator.domain.run_enums import UploadStatus
from automator.domain.youtube import AUTHORIZATION_EXPIRED_CODE, ChannelProfile
from automator.shared.errors import UpstreamFailure
from tests.fixtures.harness import Harness
from tests.fixtures.use_cases import (
    approved_run,
    complete_connect,
    list_playlists,
    publish_run,
    start_connect,
)


def channel_status(harness: Harness, channel_id: str = "chan-1") -> ChannelStatus:
    channel = harness.channels.get(channel_id)
    assert channel is not None
    return channel.status


@pytest.mark.parametrize(
    ("code", "status"),
    [
        (AUTHORIZATION_EXPIRED_CODE, ChannelStatus.EXPIRED),
        ("youtube_forbidden", ChannelStatus.CONNECTED),
    ],
)
def test_playlist_listing_marks_the_channel_expired_on_invalid_grant(
    harness: Harness, channel: Channel, code: str, status: ChannelStatus
) -> None:
    harness.youtube.failing_operations.add("list_playlists")
    harness.youtube.failure_code = code
    with pytest.raises(UpstreamFailure) as raised:
        list_playlists(harness).execute(channel.id)
    assert raised.value.code == code
    assert channel_status(harness) is status


def test_upload_with_an_expired_grant_fails_and_marks_the_channel(harness: Harness) -> None:
    run = approved_run(harness)
    harness.youtube.failing_videos.add("en-landscape.mp4")
    harness.youtube.failure_code = AUTHORIZATION_EXPIRED_CODE
    upload = publish_run(harness).execute(run.id).uploads[0]
    assert upload.status is UploadStatus.FAILED
    assert channel_status(harness) is ChannelStatus.EXPIRED


def test_an_extra_step_with_an_expired_grant_marks_the_channel(harness: Harness) -> None:
    run = approved_run(harness)
    harness.youtube.failing_operations.add("set_thumbnail")
    harness.youtube.failure_code = AUTHORIZATION_EXPIRED_CODE
    upload = publish_run(harness).execute(run.id).uploads[0]
    assert upload.status is UploadStatus.DONE and "thumbnail" in (upload.error or "")
    assert channel_status(harness) is ChannelStatus.EXPIRED


def test_marking_skips_deleted_and_already_expired_channels(
    harness: Harness, channel: Channel
) -> None:
    expired = channel.model_copy(update={"status": ChannelStatus.EXPIRED})
    harness.channels.save(expired)
    harness.expiry.mark_expired(channel)
    assert harness.channels.get(channel.id) == expired
    harness.channels.delete(channel.id)
    harness.expiry.mark_expired(channel)
    assert harness.channels.get(channel.id) is None


def test_reconnecting_restores_the_connected_status(harness: Harness, channel: Channel) -> None:
    harness.channels.save(channel.model_copy(update={"status": ChannelStatus.EXPIRED}))
    harness.youtube.profile = ChannelProfile(
        youtube_channel_id=channel.youtube_channel_id, title="T"
    )
    state = start_connect(harness).execute(channel.credential_id).state
    assert complete_connect(harness).execute("code", state).id == channel.id
    assert channel_status(harness) is ChannelStatus.CONNECTED


def test_other_errors_leave_the_channel_connected(harness: Harness, channel: Channel) -> None:
    with pytest.raises(RuntimeError), harness.expiry.watching(channel):
        raise RuntimeError("boom")
    assert channel_status(harness) is ChannelStatus.CONNECTED
