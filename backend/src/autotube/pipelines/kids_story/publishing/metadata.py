from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from autotube.domain.upload_details import DESCRIPTION_MAX_BYTES
from autotube.pipelines.kids_story.artifacts import SHORT
from autotube.pipelines.kids_story.publishing.limits import (
    TITLE_MAX,
    cleaned,
    tags_within,
    truncated,
    truncated_bytes,
)
from autotube.pipelines.kids_story.publishing.templates import template_values
from autotube.pipelines.kids_story.settings.root import KidsStorySettings
from autotube.pipelines.kids_story.story.model import Story
from autotube.pipelines.kids_story.text.templates import render_template


class UploadMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    title: str
    description: str
    tags: list[str]
    hashtags: list[str]
    category_id: str
    default_language: str
    made_for_kids: bool = True
    playlist_title: str


def upload_metadata(story: Story, settings: KidsStorySettings, variant: str) -> UploadMetadata:
    language = story.language
    metadata = settings.metadata
    values = template_values(story, settings)
    title_template = metadata.short_title_template if variant == SHORT else metadata.title_template
    title = render_template(title_template.for_language(language), values)
    description = render_template(metadata.description_template.for_language(language), values)
    return UploadMetadata(
        title=truncated(cleaned(title), TITLE_MAX),
        description=truncated_bytes(cleaned(description), DESCRIPTION_MAX_BYTES),
        tags=tags_within(metadata.tags.for_language(language)),
        hashtags=metadata.hashtags.for_language(language),
        category_id=metadata.category.value,
        default_language=language,
        playlist_title=render_template(metadata.playlist_title.for_language(language), values),
    )
