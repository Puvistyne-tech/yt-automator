from __future__ import annotations

from autotube.domain.pipeline import Pipeline
from autotube.domain.pipeline_engine import PipelineEngine
from autotube.pipelines.narrated_video.engine import NarratedVideoEngine
from autotube.pipelines.narrated_video.plugin import KidsStoryPipeline


def installed_pipelines() -> tuple[Pipeline, ...]:
    return (KidsStoryPipeline(),)


def installed_engines() -> tuple[PipelineEngine, ...]:
    return (NarratedVideoEngine(),)
