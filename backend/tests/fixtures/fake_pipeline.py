from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from automator.domain.capabilities import Capability, TextRequest
from automator.domain.pipeline import NewArtifact, Pipeline, Stage, StageContext, StageOutcome
from automator.domain.pipeline_descriptors import (
    KIDS_CONTENT,
    Aspect,
    LanguageOption,
    PipelineDescriptor,
    StageDescriptor,
    VariantOption,
    default_settings_of,
    settings_schema_of,
)
from automator.domain.quality import ScoreItem
from automator.domain.run_enums import ArtifactKind

LANGUAGES = (LanguageOption(code="en", name="English"), LanguageOption(code="ta", name="Tamil"))
VARIANTS = (
    VariantOption(id="landscape", name="Landscape", aspect=Aspect.LANDSCAPE),
    VariantOption(id="short", name="Short", aspect=Aspect.PORTRAIT),
)


class FakeSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    topic: str = Field(default="cats", min_length=1)
    fail_stage: str = ""
    score: float = Field(default=90.0, ge=0, le=100)
    with_thumbnail: bool = True


def settings_of(context: StageContext) -> FakeSettings:
    assert isinstance(context.settings, FakeSettings)
    return context.settings


def write(context: StageContext, name: str, text: str) -> Path:
    path = context.workspace / name
    path.write_text(text, encoding="utf-8")
    return path


@dataclass(frozen=True)
class FakeStage:
    descriptor: StageDescriptor
    calls: list[str] = field(default_factory=list)
    hook: Callable[[StageContext], None] | None = None

    def run(self, context: StageContext) -> StageOutcome:
        self.calls.append(context.run_id)
        if self.hook is not None:
            self.hook(context)
        settings = settings_of(context)
        if settings.fail_stage == self.descriptor.id:
            raise RuntimeError(f"{self.descriptor.id} exploded")
        context.log(f"{self.descriptor.id} running")
        return StageOutcome(
            artifacts=tuple(self.produce(context, settings)),
            provider="fake",
            message=f"{self.descriptor.id} done",
        )

    def produce(self, context: StageContext, settings: FakeSettings) -> list[NewArtifact]:
        stage_id = self.descriptor.id
        if stage_id == "script":
            return [self.script(context, settings, language) for language in context.languages]
        if stage_id == "render":
            return [
                artifact
                for language in context.languages
                for variant in VARIANTS
                for artifact in self.media(context, settings, language, variant.id)
            ]
        return [item for language in context.languages for item in self.package(context, language)]

    def script(self, context: StageContext, settings: FakeSettings, language: str) -> NewArtifact:
        text = context.providers.resolve(Capability.LLM).generate(
            TextRequest(prompt=settings.topic)
        )
        path = write(context, f"script-{language}.txt", text)
        return NewArtifact(
            kind=ArtifactKind.TEXT, path=path, language=language, media_type="text/plain"
        )

    def media(
        self, context: StageContext, settings: FakeSettings, language: str, variant: str
    ) -> tuple[NewArtifact, ...]:
        video = write(context, f"{language}-{variant}.mp4", settings.topic)
        thumb = write(context, f"{language}-{variant}.png", "png")
        made = NewArtifact(
            kind=ArtifactKind.VIDEO,
            path=video,
            language=language,
            variant=variant,
            media_type="video/mp4",
        )
        if not settings.with_thumbnail:
            return (made,)
        thumbnail = NewArtifact(
            kind=ArtifactKind.THUMBNAIL,
            path=thumb,
            language=language,
            variant=variant,
            media_type="image/png",
        )
        return (made, thumbnail)

    def package(self, context: StageContext, language: str) -> tuple[NewArtifact, ...]:
        captions = write(context, f"{language}.srt", "1\n00:00:00,000 --> 00:00:01,000\nhi\n")
        metadata = write(context, f"{language}.json", "{}")
        return (
            NewArtifact(
                kind=ArtifactKind.SUBTITLE,
                path=captions,
                language=language,
                media_type="application/x-subrip",
            ),
            NewArtifact(
                kind=ArtifactKind.METADATA,
                path=metadata,
                language=language,
                media_type="application/json",
                meta={"title": f"Story in {language}", "description": "A story", "tags": ["kids"]},
            ),
        )


STAGE_IDS = ("script", "render", "package")


@dataclass(frozen=True)
class FakePipeline:
    type_id: str = "fake"
    capabilities: tuple[str, ...] = ()
    stage_list: tuple[FakeStage, ...] = field(
        default_factory=lambda: tuple(
            FakeStage(StageDescriptor(id=stage_id, title=stage_id.title()))
            for stage_id in STAGE_IDS
        )
    )
    raise_on_score: bool = False

    @property
    def descriptor(self) -> PipelineDescriptor:
        return PipelineDescriptor(
            type_id=self.type_id,
            name=self.type_id.replace("_", " ").title(),
            version="1.0.0",
            settings_schema=settings_schema_of(FakeSettings),
            default_settings=default_settings_of(FakeSettings),
            stages=tuple(stage.descriptor for stage in self.stage_list),
            languages=LANGUAGES,
            variants=VARIANTS,
            capabilities=self.capabilities,
        )

    @property
    def settings_model(self) -> type[BaseModel]:
        return FakeSettings

    def stages(self) -> Sequence[Stage]:
        return self.stage_list

    def score(self, context: StageContext) -> Sequence[ScoreItem]:
        if self.raise_on_score:
            raise RuntimeError("scorer offline")
        return [ScoreItem(id="quality", title="Quality", score=settings_of(context).score)]


def kids_pipeline() -> FakePipeline:
    return FakePipeline(type_id="fake_kids", capabilities=(KIDS_CONTENT,))


class FakePipelineRegistry:
    def __init__(self, pipelines: Sequence[Pipeline]) -> None:
        self.pipelines = {pipeline.descriptor.type_id: pipeline for pipeline in pipelines}

    def list(self) -> list[Pipeline]:
        return list(self.pipelines.values())

    def get(self, type_id: str) -> Pipeline | None:
        return self.pipelines.get(type_id)
