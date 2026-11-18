from __future__ import annotations

from automator.domain.pipeline import Pipeline
from automator.pipelines.kids_story.plugin import KidsStoryPipeline


def installed_pipelines() -> tuple[Pipeline, ...]:
    return (KidsStoryPipeline(),)
