from __future__ import annotations

from datetime import datetime, timedelta

from pydantic import Field

from autotube.domain.model_base import DomainModel

MAX_AUTO_RETRIES = 10
MAX_RETRY_DELAY_MINUTES = 24 * 60


class RetryPolicy(DomainModel):
    auto_retry_count: int = Field(
        default=0,
        ge=0,
        le=MAX_AUTO_RETRIES,
        description="How many times a failed run is retried on its own, from the failed stage.",
    )
    retry_delay_minutes: int = Field(
        default=10,
        ge=0,
        le=MAX_RETRY_DELAY_MINUTES,
        description="Minutes to wait after a failure before retrying automatically.",
    )


def next_retry_at(policy: RetryPolicy, retries_used: int, failed_at: datetime) -> datetime | None:
    if retries_used >= policy.auto_retry_count:
        return None
    return failed_at + timedelta(minutes=policy.retry_delay_minutes)
