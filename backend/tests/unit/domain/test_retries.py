from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from automator.domain.retries import RetryPolicy, next_retry_at

AT = datetime(2026, 1, 5, 10, tzinfo=UTC)


def test_defaults_never_retry() -> None:
    assert RetryPolicy() == RetryPolicy(auto_retry_count=0, retry_delay_minutes=10)
    assert next_retry_at(RetryPolicy(), 0, AT) is None


@pytest.mark.parametrize(("used", "expected"), [(0, AT + timedelta(minutes=5)), (1, None)])
def test_next_retry_at_counts_used_retries(used: int, expected: datetime | None) -> None:
    policy = RetryPolicy(auto_retry_count=1, retry_delay_minutes=5)
    assert next_retry_at(policy, used, AT) == expected


def test_a_zero_delay_retries_at_once() -> None:
    assert next_retry_at(RetryPolicy(auto_retry_count=3, retry_delay_minutes=0), 2, AT) == AT


@pytest.mark.parametrize(
    "bad",
    [
        {"auto_retry_count": -1},
        {"auto_retry_count": 11},
        {"retry_delay_minutes": -1},
        {"retry_delay_minutes": 1441},
    ],
)
def test_retry_policy_bounds(bad: dict[str, int]) -> None:
    with pytest.raises(ValidationError):
        RetryPolicy.model_validate(bad)
