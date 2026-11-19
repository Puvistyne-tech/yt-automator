from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic.config import JsonDict

from autotube.domain.model_base import JsonObject
from autotube.pipelines.narrated_video.settings.base import (
    LocalizedList,
    LocalizedText,
)
from autotube.pipelines.narrated_video.settings.choices import (
    CATEGORY_CHOICES,
    enum_choices,
)
from autotube.pipelines.narrated_video.settings.look_choices import (
    CUSTOM_STYLE,
    card_choices,
    style_entries,
)
from autotube.pipelines.narrated_video.settings.metadata import YouTubeCategory
from autotube.pipelines.narrated_video.settings.story_choices import STRUCTURE_CHOICES, Structure

DEFAULT_STYLE_ENTRY: JsonDict = {"const": "", "title": "Keep the default style"}


class Length(StrEnum):
    SHORT = "short"
    STANDARD = "standard"
    LONG = "long"


LENGTH_CHOICES = enum_choices(
    Length,
    {
        "short": "Short, about a minute",
        "standard": "Standard, two to three minutes",
        "long": "Long, about five minutes",
    },
)
DEFINITION_STYLE_CHOICES = card_choices(
    [DEFAULT_STYLE_ENTRY, *(entry for entry in style_entries() if entry["const"] != CUSTOM_STYLE)]
)


def text_field(title: str, description: str, max_length: int = 300) -> Any:
    return Field(default="", max_length=max_length, title=title, description=description)


def localized_text_field(title: str, description: str) -> Any:
    return Field(default_factory=LocalizedText, title=title, description=description)


def localized_list_field(title: str, description: str) -> Any:
    return Field(default_factory=LocalizedList, title=title, description=description)


def paths_field(title: str, description: str) -> Any:
    return Field(default_factory=list, title=title, description=description)


class NarratedDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, title="Narrated video template")

    structure: Structure = Field(
        default=Structure.STORY,
        json_schema_extra=STRUCTURE_CHOICES,
        title="Format",
        description="How every script is built; it cannot change after the template is created.",
    )
    brief: str = text_field(
        "What the videos are about", "Describe the subject in a few sentences.", 2000
    )
    length: Length = Field(
        default=Length.STANDARD,
        json_schema_extra=LENGTH_CHOICES,
        title="Video length",
        description="How long each episode runs.",
    )
    tone: str = text_field("Tone", "How the scripts should feel; leave empty for the default.")
    topics: list[str] = Field(
        default_factory=list,
        title="Topics",
        description="Subjects the videos take turns covering; leave empty for the default.",
    )
    visual_style: str = Field(
        default="",
        json_schema_extra=DEFINITION_STYLE_CHOICES,
        title="Visual style",
        description="How the pictures look.",
    )
    music_mood: str = text_field(
        "Music mood", "Describe the background music; leave empty for the default."
    )
    title_template: LocalizedText = localized_text_field(
        "Episode title", "The title in each language; leave a language empty for the default."
    )
    short_title_template: LocalizedText = localized_text_field(
        "Short video title",
        "The Short's title in each language; leave a language empty for the default.",
    )
    description_template: LocalizedText = localized_text_field(
        "Video description",
        "The description in each language; leave a language empty for the default.",
    )
    tags: LocalizedList = localized_list_field(
        "Search tags", "Tags in each language; leave a language empty for the default."
    )
    hashtags: LocalizedList = localized_list_field(
        "Hashtags", "Hashtags in each language; leave a language empty for the default."
    )
    category: YouTubeCategory = Field(
        default=YouTubeCategory.FILM_AND_ANIMATION,
        json_schema_extra=CATEGORY_CHOICES,
        title="YouTube category",
        description="The category every video is listed under.",
    )
    basic: list[str] = paths_field(
        "Simple view settings",
        "Settings shown in the Simple view of an automation; leave empty for the default.",
    )
    hidden: list[str] = paths_field(
        "Hidden settings", "Settings never shown when editing an automation."
    )
    settings: JsonObject = Field(
        default_factory=dict,
        title="Expert settings",
        description="Exact settings applied on top of everything above.",
    )
