from __future__ import annotations

import shutil

from automator.domain.pipeline import NewArtifact, StageContext, StageOutcome
from automator.domain.pipeline_descriptors import StageDescriptor
from automator.domain.run_enums import ArtifactKind
from automator.pipelines.kids_story.art.cards import lettered_or_plain, lettering_for
from automator.pipelines.kids_story.art.lettering import Placement
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
from automator.pipelines.kids_story.stages.common import JSON, PNG, SRT, kids_settings, load_story
from automator.pipelines.kids_story.story.model import Story


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
        return StageOutcome(artifacts=tuple(made), provider="pillow", message=f"{len(made)} files")

    def thumbnail(
        self, context: StageContext, settings: KidsStorySettings, story: Story, variant: str
    ) -> NewArtifact:
        art = required(context.artifacts, Role.THUMBNAIL_ART, variant=variant)
        output = folder(context, "package") / f"thumbnail-{story.language}-{variant}.png"
        lines = [story.title] if settings.thumbnail.title_text else []
        lettering = lettering_for(
            settings,
            lines,
            story.language,
            Placement(settings.thumbnail.text_position.value),
            settings.thumbnail.text_size_ratio,
        )
        has_title = lettered_or_plain(path_of(context, art), output, lettering)
        if lines and not has_title:
            context.log(f"thumbnail for {story.language} {variant} has no title: no usable font")
        return artifact(
            ArtifactKind.THUMBNAIL,
            output,
            PNG,
            Role.THUMBNAIL,
            language=story.language,
            variant=variant,
            title_drawn=has_title,
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
        subtitles = settings.subtitles
        if not (subtitles.enabled and subtitles.upload_captions):
            return []
        source = required(context.artifacts, Role.CAPTIONS, language, variant)
        output = folder(context, "package") / f"captions-{language}-{variant}.srt"
        shutil.copyfile(path_of(context, source), output)
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
