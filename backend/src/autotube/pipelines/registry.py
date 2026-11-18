from __future__ import annotations

from autotube.domain.pipeline import Pipeline
from autotube.pipelines.kids_story.plugin import KidsStoryPipeline


def installed_pipelines() -> tuple[Pipeline, ...]:
    return (KidsStoryPipeline(),)
