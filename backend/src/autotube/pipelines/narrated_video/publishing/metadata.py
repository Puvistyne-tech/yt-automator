from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from autotube.domain.upload_details import DESCRIPTION_MAX_BYTES
from autotube.pipelines.narrated_video.artifacts import SHORT
from autotube.pipelines.narrated_video.publishing.limits import (
    TITLE_MAX,
    cleaned,
    tags_within,
    truncated,
    truncated_bytes,
)
from autotube.pipelines.narrated_video.publishing.templates import template_values
from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.story.model import Story
from autotube.pipelines.narrated_video.text.templates import filled_template


class UploadMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    title: str = Field(min_length=1)
    description: str
    tags: list[str]
    hashtags: list[str]
    category_id: str
    default_language: str
    made_for_kids: bool
    playlist_title: str


def title_or_script_title(rendered: str, story: Story) -> str:
    return cleaned(rendered) or cleaned(story.title)


def upload_metadata(story: Story, settings: KidsStorySettings, variant: str) -> UploadMetadata:
    language = story.language
    metadata = settings.metadata
    values = template_values(story, settings)
    title_template = metadata.short_title_template if variant == SHORT else metadata.title_template
    title = filled_template(title_template.for_language(language), values)
    description = filled_template(metadata.description_template.for_language(language), values)
    return UploadMetadata(
        title=truncated(title_or_script_title(title, story), TITLE_MAX),
        description=truncated_bytes(cleaned(description), DESCRIPTION_MAX_BYTES),
        tags=tags_within(metadata.tags.for_language(language)),
        hashtags=metadata.hashtags.for_language(language),
        category_id=metadata.category.value,
        default_language=language,
        made_for_kids=settings.safety.for_kids,
        playlist_title=filled_template(metadata.playlist_title.for_language(language), values),
    )
