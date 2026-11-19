from __future__ import annotations

from typing import Any

from pydantic import Field

from autotube.pipelines.narrated_video.settings.base import (
    LocalizedNumber,
    SettingsSection,
    localized_number,
)


def weight(default: float, title: str) -> Any:
    return Field(
        default=default,
        ge=0,
        le=10,
        title=title,
        description="How much this check counts in the overall score. 0 turns it off.",
    )


class ScoreWeights(SettingsSection):
    subtitle_timing: float = weight(2.0, "Subtitle timing")
    episode_duration: float = weight(1.5, "Episode length")
    short_duration: float = weight(1.0, "Short length")
    speaking_rate: float = weight(1.0, "Speaking rate")
    reading_level: float = weight(1.0, "Reading level")
    moral_and_refrain: float = weight(1.5, "Moral and refrain")
    character_consistency: float = weight(1.0, "Character consistency")
    structure: float = weight(1.5, "Structure")
    metadata_limits: float = weight(1.0, "Metadata limits")
    loudness: float = weight(0.5, "Loudness")
    completeness: float = weight(2.0, "Every output present")


class QualitySettings(SettingsSection):
    weights: ScoreWeights = Field(
        default_factory=ScoreWeights,
        title="Weights",
        description="How much each check counts towards the overall score.",
    )
    subtitle_min_coverage: float = Field(
        default=0.95,
        ge=0,
        le=1,
        title="Subtitle coverage",
        description="Share of narrated words the subtitles must show.",
    )
    words_per_minute_min: LocalizedNumber = localized_number(
        80, 50, "Slowest speaking rate", "Measured words per minute below this lose points."
    )
    words_per_minute_max: LocalizedNumber = localized_number(
        160, 120, "Fastest speaking rate", "Measured words per minute above this lose points."
    )
    loudness_tolerance_lu: float = Field(
        default=2.0,
        ge=0,
        le=20,
        title="Loudness tolerance",
        description="How far the measured loudness may be from the target, in LU.",
    )
    points_lost_per_lu: float = Field(
        default=10.0,
        ge=0,
        le=100,
        title="Points lost per LU",
        description="Score lost per loudness unit outside the tolerance.",
    )
    points_lost_per_second: float = Field(
        default=2.0,
        ge=0,
        le=100,
        title="Points lost per second",
        description="Score lost per second a video is outside its allowed length.",
    )
    points_lost_per_wpm: float = Field(
        default=2.0,
        ge=0,
        le=100,
        title="Points lost per word per minute",
        description="Score lost per word per minute outside the speaking rate range.",
    )
    points_lost_per_problem: float = Field(
        default=50.0,
        ge=0,
        le=100,
        title="Points lost per story problem",
        description="Score lost per reading level or ending problem found in a story.",
    )
    subtitle_overlap_penalty: float = Field(
        default=0.5,
        ge=0,
        le=1,
        title="Overlapping subtitle factor",
        description="The subtitle score is multiplied by this when any two subtitles overlap.",
    )
    subtitle_out_of_bounds_penalty: float = Field(
        default=0.5,
        ge=0,
        le=1,
        title="Out of bounds subtitle factor",
        description="The subtitle score is multiplied by this when a subtitle runs past the video.",
    )
