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

ENGINE_STYLE_ENTRY: JsonDict = {"const": "", "title": "Keep the engine's style"}


class Length(StrEnum):
    SHORT = "short"
    STANDARD = "standard"
    LONG = "long"


LENGTH_CHOICES = enum_choices(
    Length,
    {
        "short": "Short, about a minute",
        "standard": "Standard, two to three minutes",
        "long": "Long",
    },
)
DEFINITION_STYLE_CHOICES = card_choices(
    [ENGINE_STYLE_ENTRY, *(entry for entry in style_entries() if entry["const"] != CUSTOM_STYLE)]
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
        title="Structure",
        description="The shape of every script. Fixed once the template is created.",
    )
    brief: str = text_field(
        "Brief", "What the videos are about, in a few sentences. Empty adds nothing.", 2000
    )
    length: Length = Field(
        default=Length.STANDARD,
        json_schema_extra=LENGTH_CHOICES,
        title="Length",
        description="How long each episode runs. Standard keeps the engine's length.",
    )
    tone: str = text_field("Tone", "How the scripts feel. Empty keeps the engine's tone.")
    topics: list[str] = Field(
        default_factory=list,
        title="Topics",
        description="Themes the writer rotates through. Empty keeps the engine's themes.",
    )
    visual_style: str = Field(
        default="",
        json_schema_extra=DEFINITION_STYLE_CHOICES,
        title="Visual style",
        description="A style from the style library. Empty keeps the engine's style.",
    )
    music_mood: str = text_field(
        "Music mood", "Describes the music to the music model. Empty keeps the engine's mood."
    )
    title_template: LocalizedText = localized_text_field(
        "Episode title", "Episode title per language. An empty language keeps the engine's."
    )
    short_title_template: LocalizedText = localized_text_field(
        "Short title", "Short title per language. An empty language keeps the engine's."
    )
    description_template: LocalizedText = localized_text_field(
        "Description", "Description per language. An empty language keeps the engine's."
    )
    tags: LocalizedList = localized_list_field(
        "Tags", "Search tags per language. An empty language keeps the engine's."
    )
    hashtags: LocalizedList = localized_list_field(
        "Hashtags", "Hashtags per language. An empty language keeps the engine's."
    )
    category: YouTubeCategory = Field(
        default=YouTubeCategory.FILM_AND_ANIMATION,
        json_schema_extra=CATEGORY_CHOICES,
        title="Category",
        description="The YouTube category of every upload.",
    )
    basic: list[str] = paths_field(
        "Simple view settings",
        "Dotted settings paths shown in the Simple view. Empty keeps the engine's list.",
    )
    hidden: list[str] = paths_field(
        "Hidden settings", "Dotted settings paths never shown in the automation editor."
    )
    settings: JsonObject = Field(
        default_factory=dict,
        title="Advanced settings",
        description="Settings merged over the engine defaults after every field above.",
    )
