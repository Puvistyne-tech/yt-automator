from __future__ import annotations

from autotube.application.trend_finder import TrendFinder
from autotube.domain.channels import ChannelStatus
from autotube.domain.trends import TrendingVideo, TrendOrigin, TrendQuery
from tests.fixtures.builders import add_channel, add_credential
from tests.fixtures.harness import Harness

QUERY = TrendQuery(region="GB", category="27", limit=7)
SAMPLE = TrendingVideo(title="Sample tide pools", channel_title="Shore Notes")


class RecordingSample:
    def __init__(self) -> None:
        self.queries: list[TrendQuery] = []

    def trending(self, query: TrendQuery) -> list[TrendingVideo]:
        self.queries.append(query)
        return [SAMPLE]


def finder(harness: Harness, sample: RecordingSample) -> TrendFinder:
    h = harness
    return TrendFinder(
        h.channels, h.credentials, h.authorizer, h.youtube, h.quota_report, h.expiry, sample
    )


def used_units(harness: Harness) -> int:
    return harness.ledger.used_today("cred-1", harness.quota_report.today())


def test_without_a_connected_channel_the_sample_is_used(harness: Harness) -> None:
    sample = RecordingSample()
    report = finder(harness, sample).find(QUERY)
    assert (report.origin, report.videos) == (TrendOrigin.SAMPLE, (SAMPLE,))
    assert sample.queries == [QUERY]
    assert harness.youtube.calls == []


def test_a_connected_channel_asks_youtube_and_records_the_quota(harness: Harness) -> None:
    add_credential(harness)
    add_channel(harness)
    report = finder(harness, RecordingSample()).find(QUERY)
    assert report.origin is TrendOrigin.YOUTUBE
    assert report.videos == tuple(harness.youtube.popular)
    assert harness.youtube.queries == [QUERY]
    assert harness.youtube.tokens == ["tok"]
    assert used_units(harness) == harness.quota_report.policy.trending_units


def test_a_youtube_failure_falls_back_to_the_sample(harness: Harness) -> None:
    add_credential(harness)
    add_channel(harness)
    harness.youtube.failing_operations.add("popular_videos")
    report = finder(harness, RecordingSample()).find(QUERY)
    assert report.origin is TrendOrigin.SAMPLE
    assert used_units(harness) == 1


def test_an_expired_authorization_marks_the_channel_and_falls_back(harness: Harness) -> None:
    add_credential(harness)
    add_channel(harness)
    harness.youtube.failing_operations.add("popular_videos")
    harness.youtube.failure_code = "youtube_invalid_grant"
    report = finder(harness, RecordingSample()).find(QUERY)
    stored = harness.channels.get("chan-1")
    assert report.origin is TrendOrigin.SAMPLE
    assert stored is not None
    assert stored.status is ChannelStatus.EXPIRED


def test_an_empty_chart_falls_back_to_the_sample(harness: Harness) -> None:
    add_credential(harness)
    add_channel(harness)
    harness.youtube.popular = []
    assert finder(harness, RecordingSample()).find(QUERY).origin is TrendOrigin.SAMPLE


def test_a_missing_token_falls_back_without_charging(harness: Harness) -> None:
    add_credential(harness)
    add_channel(harness, token=None)
    report = finder(harness, RecordingSample()).find(QUERY)
    assert report.origin is TrendOrigin.SAMPLE
    assert (used_units(harness), harness.youtube.calls) == (0, [])


def test_a_missing_credential_falls_back_without_calling(harness: Harness) -> None:
    add_channel(harness)
    report = finder(harness, RecordingSample()).find(QUERY)
    assert (report.origin, harness.youtube.calls) == (TrendOrigin.SAMPLE, [])


def test_an_exhausted_quota_falls_back_without_calling(harness: Harness) -> None:
    add_credential(harness, quota=0)
    add_channel(harness)
    report = finder(harness, RecordingSample()).find(QUERY)
    assert (report.origin, harness.youtube.calls, used_units(harness)) == (
        TrendOrigin.SAMPLE,
        [],
        0,
    )
