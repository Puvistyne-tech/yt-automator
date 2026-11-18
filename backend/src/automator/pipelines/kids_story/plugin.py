from __future__ import annotations

from collections.abc import Sequence

from pydantic import BaseModel

from automator.domain.model_base import JsonObject
from automator.domain.pipeline import Stage, StageContext
from automator.domain.pipeline_descriptors import (
    KIDS_CONTENT,
    Aspect,
    LanguageOption,
    PipelineDescriptor,
    VariantOption,
    default_settings_of,
    settings_schema_of,
)
from automator.domain.quality import ScoreItem
from automator.pipelines.kids_story.artifacts import EPISODE, SHORT
from automator.pipelines.kids_story.languages import LANGUAGE_NAMES
from automator.pipelines.kids_story.resources import resource_json
from automator.pipelines.kids_story.scoring.score import score_run
from automator.pipelines.kids_story.settings.root import KidsStorySettings
from automator.pipelines.kids_story.stages.art import ArtStage
from automator.pipelines.kids_story.stages.assemble import AssembleStage
from automator.pipelines.kids_story.stages.motion import MotionStage
from automator.pipelines.kids_story.stages.music import MusicStage
from automator.pipelines.kids_story.stages.package import PackageStage
from automator.pipelines.kids_story.stages.story import StoryStage
from automator.pipelines.kids_story.stages.voice import VoiceStage

TYPE_ID = "kids_story"
VERSION = "1.0.0"
NAME = "Kutty Stories"
DESCRIPTION = (
    "Short, gentle animated stories for young children, in English and Tamil. Each run makes a "
    "2 to 3 minute 16:9 episode and a vertical Short per language, with exact subtitles, a "
    "thumbnail and upload details."
)
VARIANTS = (
    VariantOption(
        id=EPISODE,
        name="Episode",
        aspect=Aspect.LANDSCAPE,
        description="The full 16:9 story with intro and outro cards.",
    ),
    VariantOption(
        id=SHORT,
        name="Short",
        aspect=Aspect.PORTRAIT,
        description="A vertical 9:16 cut of the best scenes, opened by a hook line.",
    ),
)


def ui_schema() -> JsonObject:
    loaded = resource_json("ui", "schema.json")
    return loaded if isinstance(loaded, dict) else {}


class KidsStoryPipeline:
    def __init__(self) -> None:
        self.stage_list: tuple[Stage, ...] = (
            StoryStage(),
            VoiceStage(),
            ArtStage(),
            MotionStage(),
            MusicStage(),
            AssembleStage(),
            PackageStage(),
        )

    @property
    def descriptor(self) -> PipelineDescriptor:
        return PipelineDescriptor(
            type_id=TYPE_ID,
            name=NAME,
            description=DESCRIPTION,
            version=VERSION,
            settings_schema=settings_schema_of(KidsStorySettings),
            default_settings=default_settings_of(KidsStorySettings),
            ui_schema=ui_schema(),
            stages=tuple(stage.descriptor for stage in self.stage_list),
            languages=tuple(
                LanguageOption(code=code, name=name) for code, name in LANGUAGE_NAMES.items()
            ),
            variants=VARIANTS,
            capabilities=(KIDS_CONTENT,),
        )

    @property
    def settings_model(self) -> type[BaseModel]:
        return KidsStorySettings

    def stages(self) -> Sequence[Stage]:
        return self.stage_list

    def score(self, context: StageContext) -> Sequence[ScoreItem]:
        return score_run(context)
