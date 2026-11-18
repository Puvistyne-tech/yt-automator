from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime

from pydantic import Field

from automator.domain.model_base import DomainModel
from automator.shared.clock import local_date


class QuotaPolicy(DomainModel):
    video_units: int = Field(default=1600, ge=0)
    thumbnail_units: int = Field(default=50, ge=0)
    caption_units: int = Field(default=400, ge=0)
    playlist_item_units: int = Field(default=50, ge=0)
    reset_timezone: str = "America/Los_Angeles"

    def quota_day(self, moment: datetime) -> date:
        return local_date(moment, self.reset_timezone)


class QuotaUsage(DomainModel):
    credential_id: str
    name: str
    used: int
    limit: int

    @property
    def remaining(self) -> int:
        return max(self.limit - self.used, 0)


class QuotaShortfall(DomainModel):
    credential_id: str
    needed: int
    remaining: int


def upload_cost(
    policy: QuotaPolicy, *, thumbnail: bool, caption_tracks: int, playlist: bool
) -> int:
    return (
        policy.video_units
        + (policy.thumbnail_units if thumbnail else 0)
        + policy.caption_units * caption_tracks
        + (policy.playlist_item_units if playlist else 0)
    )


def quota_shortfalls(
    needed: Mapping[str, int], usage: Mapping[str, QuotaUsage]
) -> list[QuotaShortfall]:
    return [
        QuotaShortfall(
            credential_id=credential_id, needed=units, remaining=usage[credential_id].remaining
        )
        for credential_id, units in sorted(needed.items())
        if units > usage[credential_id].remaining
    ]
