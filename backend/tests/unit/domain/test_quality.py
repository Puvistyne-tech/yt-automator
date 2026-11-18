from __future__ import annotations

import pytest
from pydantic import ValidationError

from automator.domain.quality import (
    ReviewMode,
    ReviewPolicy,
    ScoreItem,
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
    assert ReviewPolicy() == ReviewPolicy(mode=ReviewMode.ALWAYS, min_score=85)


@pytest.mark.parametrize("bad", [{"min_score": -1}, {"min_score": 100.5}])
def test_policy_score_bounds(bad: dict[str, float]) -> None:
    with pytest.raises(ValidationError):
        ReviewPolicy.model_validate(bad)


@pytest.mark.parametrize("bad", [{"score": 101}, {"score": -1}, {"score": 50, "weight": -1}])
def test_score_item_bounds(bad: dict[str, float]) -> None:
    with pytest.raises(ValidationError):
        ScoreItem.model_validate({"id": "x", "title": "x", **bad})
