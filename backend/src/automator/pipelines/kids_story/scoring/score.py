from __future__ import annotations

from automator.domain.pipeline import StageContext
from automator.domain.quality import ScoreItem
from automator.pipelines.kids_story.scoring.content_items import (
    character_consistency,
    moral_and_refrain,
    reading_level,
)
from automator.pipelines.kids_story.scoring.inputs import ScoreInputs, ScoreRule, gathered
from automator.pipelines.kids_story.scoring.output_items import (
    completeness,
    loudness,
    metadata_limits,
)
from automator.pipelines.kids_story.scoring.timing_items import (
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
