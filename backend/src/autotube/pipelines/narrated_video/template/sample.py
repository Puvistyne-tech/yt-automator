from __future__ import annotations

from autotube.domain.pipeline import ProviderResolver
from autotube.domain.pipeline_templates import PipelineTemplate
from autotube.domain.run_enums import LogLevel
from autotube.domain.sample_scripts import SampleScene, SampleScript, SampleUnavailableError
from autotube.pipelines.narrated_video.artifacts import EPISODE
from autotube.pipelines.narrated_video.languages import ordered_languages
from autotube.pipelines.narrated_video.publishing.audience_check import (
    ChildDirectedMetadataError,
    checked_audience,
)
from autotube.pipelines.narrated_video.publishing.metadata import UploadMetadata, upload_metadata
from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.story.authoring import (
    WriterUnavailableError,
    Written,
    authored_scripts,
)
from autotube.pipelines.narrated_video.story.model import Story, StoryScene
from autotube.pipelines.narrated_video.story.shaping import shaped
from autotube.pipelines.narrated_video.story.themes import choose_theme
from autotube.pipelines.narrated_video.template.definition import NarratedDefinition
from autotube.pipelines.narrated_video.template.settings_model import settings_model_for
from autotube.shared.errors import AppError

UNAVAILABLE = (
    "The script writer is not available right now. Check the text model under Providers and "
    "try again."
)
REJECTED = (
    "The script writer did not write a script that passed the checks. Try again, or change "
    "the brief or the topic."
)


def unlogged(message: str, level: LogLevel = LogLevel.INFO) -> None:  # noqa: ARG001
    return None


def sample_scene(scene: StoryScene) -> SampleScene:
    return SampleScene.model_validate(scene.model_dump(include=set(SampleScene.model_fields)))


def preview_settings(settings: KidsStorySettings) -> KidsStorySettings:
    story = settings.story.model_copy(update={"max_attempts": settings.story.preview_attempts})
    return settings.model_copy(update={"story": story})


def sample_order(settings: KidsStorySettings, language: str) -> list[str]:
    return ordered_languages(settings.story.primary_language.value, [language])


def written_sample(
    settings: KidsStorySettings, language: str, topic: str, providers: ProviderResolver, seed: str
) -> Written:
    theme = topic.strip() or choose_theme(settings.story, seed)
    order = sample_order(settings, language)
    try:
        written = authored_scripts(
            providers, preview_settings(settings), unlogged, seed, theme, order
        )
    except (LookupError, AppError, WriterUnavailableError) as error:
        raise SampleUnavailableError(UNAVAILABLE) from error
    if written is None:
        raise SampleUnavailableError(REJECTED)
    return written


def screened_upload(story: Story, settings: KidsStorySettings) -> UploadMetadata:
    try:
        return checked_audience(upload_metadata(story, settings, EPISODE))
    except ChildDirectedMetadataError as error:
        raise SampleUnavailableError(str(error)) from error


def settings_sample(
    settings: KidsStorySettings, language: str, topic: str, providers: ProviderResolver, seed: str
) -> SampleScript:
    stories, provider = written_sample(settings, language, topic, providers, seed)
    story = shaped(stories[language], settings)
    upload = screened_upload(story, settings)
    return SampleScript(
        language=language,
        title=story.title,
        scenes=tuple(sample_scene(scene) for scene in story.scenes),
        takeaway=story.moral,
        upload_title=upload.title,
        upload_description=upload.description,
        provider=provider,
    )


def template_sample(
    template: PipelineTemplate, language: str, topic: str, providers: ProviderResolver
) -> SampleScript:
    definition = NarratedDefinition.model_validate(template.definition)
    settings = settings_model_for(definition, template.audience)()
    return settings_sample(settings, language, topic, providers, template.id)
