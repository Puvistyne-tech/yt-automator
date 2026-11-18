from __future__ import annotations

from collections.abc import Sequence
from enum import StrEnum

from pydantic import Field

from automator.domain.model_base import DomainModel
from automator.domain.run_enums import RunStatus


class ReviewMode(StrEnum):
    ALWAYS = "always"
    AUTO_WHEN_SCORE_AT_LEAST = "auto_when_score_at_least"


class ReviewPolicy(DomainModel):
    mode: ReviewMode = ReviewMode.ALWAYS
    min_score: float = Field(default=85.0, ge=0.0, le=100.0)
    reject_below: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="A run scoring under this is rejected automatically. Empty means never.",
    )
    auto_publish: bool = Field(
        default=False,
        description="Publish as soon as a run is approved, by its score or by hand.",
    )


class ScoreItem(DomainModel):
    id: str
    title: str
    score: float = Field(ge=0.0, le=100.0)
    weight: float = Field(default=1.0, ge=0.0)
    detail: str = ""


def weighted_score(items: Sequence[ScoreItem]) -> float | None:
    total_weight = sum(item.weight for item in items)
    if total_weight <= 0:
        return None
    return sum(item.score * item.weight for item in items) / total_weight


def review_policy_errors(policy: ReviewPolicy) -> dict[str, str]:
    auto = policy.mode is ReviewMode.AUTO_WHEN_SCORE_AT_LEAST
    if auto and policy.reject_below is not None and policy.reject_below >= policy.min_score:
        limit = f"{policy.min_score:g}"
        return {"reject_below": f"must be below the minimum score for auto-approval ({limit})"}
    return {}


def auto_rejection(policy: ReviewPolicy, score: float | None) -> str | None:
    if policy.reject_below is None or score is None or score >= policy.reject_below:
        return None
    return (
        f"Rejected automatically: the score {score:.1f} is below "
        f"the auto-reject threshold {policy.reject_below:g}"
    )


def status_after_scoring(policy: ReviewPolicy, score: float | None) -> RunStatus:
    if auto_rejection(policy, score) is not None:
        return RunStatus.REJECTED
    auto = policy.mode is ReviewMode.AUTO_WHEN_SCORE_AT_LEAST
    if auto and score is not None and score >= policy.min_score:
        return RunStatus.APPROVED
    return RunStatus.AWAITING_REVIEW
