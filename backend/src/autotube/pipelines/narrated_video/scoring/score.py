from __future__ import annotations

from autotube.domain.pipeline import StageContext
from autotube.domain.quality import ScoreItem
from autotube.pipelines.narrated_video.scoring.content_items import (
    character_consistency,
    moral_and_refrain,
    reading_level,
)
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

RULES: tuple[ScoreRule, ...] = (
    subtitle_timing,
    episode_duration,
    short_duration,
    speaking_rate,
    reading_level,
    moral_and_refrain,
    character_consistency,
    metadata_limits,
    loudness,
    completeness,
)


def score_items(inputs: ScoreInputs) -> list[ScoreItem]:
    return [item for rule in RULES if (item := rule(inputs)) is not None]


def score_run(context: StageContext) -> list[ScoreItem]:
    return score_items(gathered(context))
