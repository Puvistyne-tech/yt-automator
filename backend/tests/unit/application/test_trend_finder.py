from __future__ import annotations

import logging

import pytest

from autotube.domain.channels import ChannelStatus
from autotube.domain.trends import TrendingVideo, TrendOrigin, TrendQuery, TrendReport
from tests.fixtures.builders import add_channel, add_credential
from tests.fixtures.harness import Harness
from tests.fixtures.suggestion_data import StaticTrends
from tests.fixtures.template_rig import TemplateRig

QUERY = TrendQuery(region="GB", category="27", limit=7)
SAMPLE = TrendingVideo(title="Sample tide pools", channel_title="Shore Notes")
TOKEN = "stored-token-7f3a"


@pytest.fixture
def rig(harness: Harness) -> TemplateRig:
    return TemplateRig(harness, trends=StaticTrends([SAMPLE]))


@pytest.fixture
def connected(rig: TemplateRig) -> TemplateRig:
    add_credential(rig.harness)
    add_channel(rig.harness, token=TOKEN)
    return rig


def found(rig: TemplateRig) -> TrendReport:
    return rig.finder.find(QUERY)


def used_units(rig: TemplateRig) -> int:
    return rig.harness.ledger.used_today("cred-1", rig.harness.quota_report.today())


def channel_status(rig: TemplateRig) -> ChannelStatus:
    stored = rig.harness.channels.get("chan-1")
    assert stored is not None
    return stored.status


def test_without_a_connected_channel_the_sample_is_used(rig: TemplateRig) -> None:
    report = found(rig)
    assert (report.origin, report.videos) == (TrendOrigin.SAMPLE, (SAMPLE,))
    assert rig.trends.queries == [QUERY]
    assert rig.harness.youtube.calls == []


def test_a_connected_channel_asks_youtube_and_records_the_quota(connected: TemplateRig) -> None:
    youtube = connected.harness.youtube
    report = found(connected)
    assert (report.origin, report.videos) == (TrendOrigin.YOUTUBE, tuple(youtube.popular))
    assert (youtube.queries, youtube.tokens) == ([QUERY], [TOKEN])
    assert used_units(connected) == 1


def test_a_quota_exactly_covering_the_call_is_enough(rig: TemplateRig) -> None:
    add_credential(rig.harness, quota=1)
    add_channel(rig.harness)
    assert found(rig).origin is TrendOrigin.YOUTUBE
    assert used_units(rig) == 1


def test_a_youtube_failure_falls_back_and_keeps_the_channel_connected(
    connected: TemplateRig,
) -> None:
    connected.harness.youtube.failing_operations.add("popular_videos")
    assert found(connected).origin is TrendOrigin.SAMPLE
    assert (used_units(connected), channel_status(connected)) == (1, ChannelStatus.CONNECTED)


def test_a_fallback_logs_only_the_error_code(
    connected: TemplateRig, caplog: pytest.LogCaptureFixture
) -> None:
    connected.harness.youtube.failing_operations.add("popular_videos")
    with caplog.at_level(logging.WARNING, logger="autotube"):
        found(connected)
    [record] = caplog.records
    assert "upstream_failure" in record.getMessage()
    assert TOKEN not in caplog.text
    assert "rejected" not in caplog.text


def test_an_expired_authorization_marks_the_channel_and_falls_back(
    connected: TemplateRig,
) -> None:
    connected.harness.youtube.failing_operations.add("popular_videos")
    connected.harness.youtube.failure_code = "youtube_invalid_grant"
    assert found(connected).origin is TrendOrigin.SAMPLE
    assert channel_status(connected) is ChannelStatus.EXPIRED


def test_an_empty_chart_falls_back_to_the_sample(connected: TemplateRig) -> None:
    connected.harness.youtube.popular = []
    assert found(connected).origin is TrendOrigin.SAMPLE


def test_a_missing_token_falls_back_without_charging(rig: TemplateRig) -> None:
    add_credential(rig.harness)
    add_channel(rig.harness, token=None)
    assert found(rig).origin is TrendOrigin.SAMPLE
    assert (used_units(rig), rig.harness.youtube.calls) == (0, [])


def test_a_missing_credential_falls_back_without_calling(rig: TemplateRig) -> None:
    add_channel(rig.harness)
    assert (found(rig).origin, rig.harness.youtube.calls) == (TrendOrigin.SAMPLE, [])


def test_an_exhausted_quota_falls_back_without_calling(rig: TemplateRig) -> None:
    add_credential(rig.harness, quota=0)
    add_channel(rig.harness)
    report = found(rig)
    assert (report.origin, rig.harness.youtube.calls, used_units(rig)) == (
        TrendOrigin.SAMPLE,
        [],
        0,
    )
