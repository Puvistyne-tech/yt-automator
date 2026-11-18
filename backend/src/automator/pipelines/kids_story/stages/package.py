from __future__ import annotations

import shutil
from pathlib import Path

from automator.domain.pipeline import NewArtifact, StageContext, StageOutcome
from automator.domain.pipeline_descriptors import StageDescriptor
from automator.domain.run_enums import ArtifactKind, LogLevel
from automator.domain.srt import parse_srt
from automator.pipelines.kids_story.art.cards import lettered_or_plain, lettering_for
from automator.pipelines.kids_story.art.imaging import JpegBudget, saved_jpeg
from automator.pipelines.kids_story.artifacts import (
    VARIANTS,
    Role,
    artifact,
    folder,
    latest,
    path_of,
    required,
    write_json,
)
from automator.pipelines.kids_story.publishing.metadata import upload_metadata
from automator.pipelines.kids_story.settings.root import KidsStorySettings
from automator.pipelines.kids_story.settings.thumbnail import ThumbnailSettings
from automator.pipelines.kids_story.stages.media_types import JPEG, JSON, SRT
from automator.pipelines.kids_story.stages.run_settings import kids_settings
from automator.pipelines.kids_story.stages.story_loading import load_story
from automator.pipelines.kids_story.story.model import Story

LOCAL_PROVIDER = "local"


def jpeg_budget(thumbnail: ThumbnailSettings) -> JpegBudget:
    return JpegBudget(
        max_bytes=thumbnail.max_bytes,
        quality=thumbnail.jpeg_quality,
        min_quality=thumbnail.min_jpeg_quality,
        downscale_step=thumbnail.downscale_step,
        min_width=thumbnail.min_width,
    )


def has_cues(srt: Path) -> bool:
    return bool(parse_srt(srt.read_text(encoding="utf-8")))


class PackageStage:
    @property
    def descriptor(self) -> StageDescriptor:
        return StageDescriptor(
            id="package",
            title="Prepare the uploads",
            description="Thumbnails, titles, descriptions, tags and caption tracks per video.",
        )

    def run(self, context: StageContext) -> StageOutcome:
        settings = kids_settings(context)
        made: list[NewArtifact] = []
        for language in context.languages:
            story = load_story(context, language)
            for variant in VARIANTS:
                if latest(context.artifacts, Role.FINAL_VIDEO, language, variant) is None:
                    continue
                made.append(self.thumbnail(context, settings, story, variant))
                made.append(self.metadata(context, settings, story, variant))
                made.extend(self.captions(context, settings, language, variant))
        return StageOutcome(
            artifacts=tuple(made), provider=LOCAL_PROVIDER, message=f"{len(made)} files"
        )

    def thumbnail(
        self, context: StageContext, settings: KidsStorySettings, story: Story, variant: str
    ) -> NewArtifact:
        art = required(context.artifacts, Role.THUMBNAIL_ART, variant=variant)
        name = f"thumbnail-{story.language}-{variant}"
        lettered = folder(context, "package") / f"{name}-lettered.png"
        lines = [story.title] if settings.thumbnail.title_text else []
        lettering = lettering_for(
            settings,
            lines,
            story.language,
            settings.thumbnail.text_position,
            settings.thumbnail.text_size_ratio,
        )
        has_title = lettered_or_plain(path_of(context, art), lettered, lettering)
        if lines and not has_title:
            context.log(
                f"thumbnail for {story.language} {variant} has no title: no usable font",
                LogLevel.WARNING,
            )
        output = lettered.with_name(f"{name}.jpg")
        size = saved_jpeg(lettered, output, jpeg_budget(settings.thumbnail))
        lettered.unlink()
        if size > settings.thumbnail.max_bytes:
            context.log(
                f"{output.name} is still {size} bytes at the narrowest allowed width",
                LogLevel.WARNING,
            )
        return artifact(
            ArtifactKind.THUMBNAIL,
            output,
            JPEG,
            Role.THUMBNAIL,
            language=story.language,
            variant=variant,
            title_drawn=has_title,
            bytes=size,
        )

    def metadata(
        self, context: StageContext, settings: KidsStorySettings, story: Story, variant: str
    ) -> NewArtifact:
        details = upload_metadata(story, settings, variant).model_dump(mode="json")
        path = folder(context, "package") / f"metadata-{story.language}-{variant}.json"
        write_json(path, details)
        return artifact(
            ArtifactKind.METADATA,
            path,
            JSON,
            Role.UPLOAD_METADATA,
            language=story.language,
            variant=variant,
            **details,
        )

    def captions(
        self, context: StageContext, settings: KidsStorySettings, language: str, variant: str
    ) -> list[NewArtifact]:
        if not settings.subtitles.captions_uploaded:
            return []
        source = path_of(context, required(context.artifacts, Role.CAPTIONS, language, variant))
        if not has_cues(source):
            context.log(
                f"no caption track for {language} {variant}: the subtitles are empty",
                LogLevel.WARNING,
            )
            return []
        output = folder(context, "package") / f"captions-{language}-{variant}.srt"
        shutil.copyfile(source, output)
        return [
            artifact(
                ArtifactKind.SUBTITLE,
                output,
                SRT,
                Role.CAPTION_TRACK,
                language=language,
                variant=variant,
            )
        ]
