from __future__ import annotations

from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict, Field


class SegmentSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    key: str
    visual_key: str
    narration: str | None = None
    narration_seconds: float = Field(default=0.0, ge=0)
    min_seconds: float = Field(gt=0)
    scene: int | None = None


class Segment(SegmentSpec):
    start: float = Field(ge=0)
    duration: float = Field(gt=0)
    narration_start: float = Field(ge=0)

    @property
    def end(self) -> float:
        return self.start + self.duration


class Padding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    lead_in: float = Field(ge=0)
    tail: float = Field(ge=0)


def segment_seconds(spec: SegmentSpec, padding: Padding) -> float:
    if spec.narration is None:
        return spec.min_seconds
    return max(spec.min_seconds, padding.lead_in + spec.narration_seconds + padding.tail)


def laid_out(specs: Sequence[SegmentSpec], padding: Padding) -> list[Segment]:
    cursor = 0.0
    segments: list[Segment] = []
    for spec in specs:
        duration = segment_seconds(spec, padding)
        segments.append(
            Segment(
                **spec.model_dump(),
                start=cursor,
                duration=duration,
                narration_start=cursor + padding.lead_in,
            )
        )
        cursor += duration
    return segments


def total_seconds(segments: Sequence[Segment]) -> float:
    return segments[-1].end if segments else 0.0


def fit_within(
    specs: Sequence[SegmentSpec], padding: Padding, max_seconds: float
) -> list[SegmentSpec]:
    kept: list[SegmentSpec] = []
    used = 0.0
    for spec in specs:
        seconds = segment_seconds(spec, padding)
        if used + seconds <= max_seconds:
            kept.append(spec)
            used += seconds
    return kept
