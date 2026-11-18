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


def status_after_scoring(policy: ReviewPolicy, score: float | None) -> RunStatus:
    auto = policy.mode is ReviewMode.AUTO_WHEN_SCORE_AT_LEAST
    if auto and score is not None and score >= policy.min_score:
        return RunStatus.APPROVED
    return RunStatus.AWAITING_REVIEW
