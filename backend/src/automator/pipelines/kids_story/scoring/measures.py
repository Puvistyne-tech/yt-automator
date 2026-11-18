from __future__ import annotations

from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict

from automator.pipelines.kids_story.story.words import word_count
from automator.pipelines.kids_story.subtitles.srt import SrtEntry

FULL = 100.0
TOLERANCE = 1e-3


class Measured(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    score: float
    detail: str


def clamp(score: float) -> float:
    return min(max(score, 0.0), FULL)


def distance_outside(value: float, low: float, high: float) -> float:
    if value < low:
        return low - value
    return value - high if value > high else 0.0


def range_score(value: float, low: float, high: float, per_unit: float) -> float:
    return clamp(FULL - distance_outside(value, low, high) * per_unit)


def average(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else FULL


def overlaps(entries: Sequence[SrtEntry]) -> int:
    ordered = sorted(entries, key=lambda entry: entry.start)
    return sum(
        1
        for before, after in zip(ordered, ordered[1:], strict=False)
        if before.end > after.start + TOLERANCE
    )


def outside_bounds(entries: Sequence[SrtEntry], seconds: float) -> int:
    return sum(
        1
        for entry in entries
        if entry.start < 0 or entry.end <= entry.start or entry.end > seconds + TOLERANCE
    )


class SubtitleRules(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    min_coverage: float
    overlap_penalty: float
    out_of_bounds_penalty: float


def penalty_factor(count: int, factor: float) -> float:
    return factor if count else 1.0


def subtitle_track(
    entries: Sequence[SrtEntry], video_seconds: float, narrated_words: int, rules: SubtitleRules
) -> Measured:
    shown = sum(word_count(entry.text) for entry in entries)
    coverage = shown / narrated_words if narrated_words else 1.0
    overlap_count = overlaps(entries)
    outside_count = outside_bounds(entries, video_seconds)
    minimum = rules.min_coverage
    coverage_part = min(coverage / minimum, 1.0) if minimum > 0 else 1.0
    penalty = penalty_factor(overlap_count, rules.overlap_penalty) * penalty_factor(
        outside_count, rules.out_of_bounds_penalty
    )
    return Measured(
        score=clamp(FULL * coverage_part * penalty),
        detail=f"coverage {coverage:.0%}, {overlap_count} overlaps, {outside_count} out of bounds",
    )
