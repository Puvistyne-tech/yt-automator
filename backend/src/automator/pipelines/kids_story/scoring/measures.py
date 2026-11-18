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


def subtitle_track(
    entries: Sequence[SrtEntry], video_seconds: float, narrated_words: int, min_coverage: float
) -> Measured:
    shown = sum(word_count(entry.text) for entry in entries)
    coverage = shown / narrated_words if narrated_words else 1.0
    overlap_count = overlaps(entries)
    outside_count = outside_bounds(entries, video_seconds)
    coverage_part = min(coverage / min_coverage, 1.0) if min_coverage > 0 else 1.0
    penalty = (0.5 if overlap_count else 1.0) * (0.5 if outside_count else 1.0)
    return Measured(
        score=clamp(FULL * coverage_part * penalty),
        detail=f"coverage {coverage:.0%}, {overlap_count} overlaps, {outside_count} out of bounds",
    )
