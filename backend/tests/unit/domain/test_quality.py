from __future__ import annotations

import pytest
from pydantic import ValidationError

from automator.domain.quality import (
    ReviewMode,
    ReviewPolicy,
    ScoreItem,
    auto_rejection,
    review_policy_errors,
    status_after_scoring,
    weighted_score,
)
from automator.domain.run_enums import RunStatus


def item(score: float, weight: float = 1.0) -> ScoreItem:
    return ScoreItem(id=f"i{score}", title="t", score=score, weight=weight)


@pytest.mark.parametrize(
    ("items", "expected"),
    [
        ([], None),
        ([item(80)], 80.0),
        ([item(100, 3), item(0, 1)], 75.0),
        ([item(50, 0)], None),
    ],
)
def test_weighted_score(items: list[ScoreItem], expected: float | None) -> None:
    assert weighted_score(items) == expected


AUTO = ReviewPolicy(mode=ReviewMode.AUTO_WHEN_SCORE_AT_LEAST, min_score=85)


@pytest.mark.parametrize(
    ("policy", "score", "status"),
    [
        (ReviewPolicy(), 100.0, RunStatus.AWAITING_REVIEW),
        (AUTO, 85.0, RunStatus.APPROVED),
        (AUTO, 84.99, RunStatus.AWAITING_REVIEW),
        (AUTO, None, RunStatus.AWAITING_REVIEW),
        (
            ReviewPolicy(mode=ReviewMode.AUTO_WHEN_SCORE_AT_LEAST, min_score=0),
            0.0,
            RunStatus.APPROVED,
        ),
    ],
)
def test_review_policy_decision(
    policy: ReviewPolicy, score: float | None, status: RunStatus
) -> None:
    assert status_after_scoring(policy, score) is status


def test_defaults_are_safe() -> None:
    assert ReviewPolicy() == ReviewPolicy(
        mode=ReviewMode.ALWAYS, min_score=85, reject_below=None, auto_publish=False
    )


def test_a_policy_stored_before_the_new_rules_loads_with_safe_defaults() -> None:
    stored = ReviewPolicy.model_validate({"mode": "auto_when_score_at_least", "min_score": 70})
    assert (stored.reject_below, stored.auto_publish) == (None, False)


REJECTING = ReviewPolicy(reject_below=50)
AUTO_REJECTING = ReviewPolicy(
    mode=ReviewMode.AUTO_WHEN_SCORE_AT_LEAST, min_score=85, reject_below=50
)


@pytest.mark.parametrize(
    ("policy", "score", "status"),
    [
        (REJECTING, 49.9, RunStatus.REJECTED),
        (REJECTING, 50.0, RunStatus.AWAITING_REVIEW),
        (REJECTING, None, RunStatus.AWAITING_REVIEW),
        (AUTO_REJECTING, 10.0, RunStatus.REJECTED),
        (AUTO_REJECTING, 70.0, RunStatus.AWAITING_REVIEW),
        (AUTO_REJECTING, 90.0, RunStatus.APPROVED),
    ],
)
def test_auto_reject_below_a_score(
    policy: ReviewPolicy, score: float | None, status: RunStatus
) -> None:
    assert status_after_scoring(policy, score) is status


def test_auto_rejection_reason_names_score_and_threshold() -> None:
    assert auto_rejection(REJECTING, 42.25) == (
        "Rejected automatically: the score 42.2 is below the auto-reject threshold 50"
    )
    assert auto_rejection(ReviewPolicy(), 0.0) is None


@pytest.mark.parametrize(
    ("policy", "errors"),
    [
        (ReviewPolicy(), {}),
        (AUTO_REJECTING, {}),
        (ReviewPolicy(reject_below=95), {}),
        (
            ReviewPolicy(mode=ReviewMode.AUTO_WHEN_SCORE_AT_LEAST, min_score=80, reject_below=80),
            {"reject_below": "must be below the minimum score for auto-approval (80)"},
        ),
        (
            ReviewPolicy(mode=ReviewMode.AUTO_WHEN_SCORE_AT_LEAST, min_score=60, reject_below=75),
            {"reject_below": "must be below the minimum score for auto-approval (60)"},
        ),
    ],
)
def test_reject_below_must_sit_under_min_score_when_both_apply(
    policy: ReviewPolicy, errors: dict[str, str]
) -> None:
    assert review_policy_errors(policy) == errors


@pytest.mark.parametrize(
    "bad",
    [{"min_score": -1}, {"min_score": 100.5}, {"reject_below": -1}, {"reject_below": 101}],
)
def test_policy_score_bounds(bad: dict[str, float]) -> None:
    with pytest.raises(ValidationError):
        ReviewPolicy.model_validate(bad)


@pytest.mark.parametrize("bad", [{"score": 101}, {"score": -1}, {"score": 50, "weight": -1}])
def test_score_item_bounds(bad: dict[str, float]) -> None:
    with pytest.raises(ValidationError):
        ScoreItem.model_validate({"id": "x", "title": "x", **bad})
