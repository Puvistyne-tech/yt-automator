from __future__ import annotations

from autotube.domain.pipeline import StageContext
from autotube.domain.quality import ScoreItem
from autotube.pipelines.narrated_video.scoring.content_items import reading_level
from autotube.pipelines.narrated_video.scoring.inputs import ScoreInputs, ScoreRule, gathered
from autotube.pipelines.narrated_video.scoring.output_items import (
    completeness,
    loudness,
    metadata_limits,
)
from autotube.pipelines.narrated_video.scoring.timing_items import (
    episode_duration,
    short_duration,
    speaking_rate,
    subtitle_timing,
)
from autotube.pipelines.narrated_video.structures.registry import spec_of

LEADING_RULES: tuple[ScoreRule, ...] = (
    subtitle_timing,
    episode_duration,
    short_duration,
    speaking_rate,
    reading_level,
)
TRAILING_RULES: tuple[ScoreRule, ...] = (metadata_limits, loudness, completeness)


def score_rules(inputs: ScoreInputs) -> tuple[ScoreRule, ...]:
    return (*LEADING_RULES, *spec_of(inputs.settings).score_rules, *TRAILING_RULES)


def score_items(inputs: ScoreInputs) -> list[ScoreItem]:
    return [item for rule in score_rules(inputs) if (item := rule(inputs)) is not None]


def score_run(context: StageContext) -> list[ScoreItem]:
    return score_items(gathered(context))
