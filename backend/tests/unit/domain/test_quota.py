from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from automator.domain.quota import QuotaPolicy, QuotaUsage, quota_shortfalls, upload_cost

POLICY = QuotaPolicy()


@pytest.mark.parametrize(
    ("thumbnail", "captions", "playlist", "expected"),
    [
        (False, 0, False, 1600),
        (True, 0, False, 1650),
        (False, 2, False, 2400),
        (True, 1, True, 2100),
    ],
)
def test_upload_cost(thumbnail: bool, captions: int, playlist: bool, expected: int) -> None:
    cost = upload_cost(POLICY, thumbnail=thumbnail, caption_tracks=captions, playlist=playlist)
    assert cost == expected


def test_costs_are_configurable() -> None:
    policy = QuotaPolicy(video_units=100, caption_units=1)
    assert upload_cost(policy, thumbnail=False, caption_tracks=3, playlist=False) == 103


def test_quota_day_resets_in_pacific_time() -> None:
    assert POLICY.quota_day(datetime(2026, 1, 6, 7, 59, tzinfo=UTC)) == date(2026, 1, 5)
    assert POLICY.quota_day(datetime(2026, 1, 6, 8, 0, tzinfo=UTC)) == date(2026, 1, 6)


@pytest.mark.parametrize(
    ("needed", "used", "short"),
    [(1600, 8400, False), (1601, 8400, True), (1, 10000, True), (0, 12000, False)],
)
def test_shortfalls(needed: int, used: int, short: bool) -> None:
    usage = {"c1": QuotaUsage(credential_id="c1", name="C", used=used, limit=10000)}
    shortfalls = quota_shortfalls({"c1": needed}, usage)
    assert bool(shortfalls) is short
    assert usage["c1"].remaining == max(10000 - used, 0)
