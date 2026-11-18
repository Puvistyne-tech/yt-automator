from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from autotube.pipelines.kids_story.settings.base import SettingsSection
from autotube.pipelines.kids_story.settings.choices import (
    ENDING_STYLE_CHOICES,
    LEAD_MODE_CHOICES,
    STORY_CHECK_CHOICES,
)

TONE = "warm, gentle"
WRITING_STYLE = "Short sentences, simple everyday words, warm and calm tone."
QUESTION_STYLE = '"What happens next?" style questions for children'
TRANSLATION_STYLE = "natural, simple, warm"


class EndingStyle(StrEnum):
    MORAL_AND_REFRAIN = "moral_and_refrain"
    REFRAIN_ONLY = "refrain_only"
    OPEN = "open"


class LeadMode(StrEnum):
    FIXED = "fixed"
    ROTATE = "rotate"


class StoryCheck(StrEnum):
    SCENE_COUNT = "scene_count"
    WORDS_PER_SCENE = "words_per_scene"
    DURATION = "duration"
    ENDING = "ending"
    READING_LEVEL = "reading_level"
    CAST = "cast"


def says_moral(style: EndingStyle) -> bool:
    return style is EndingStyle.MORAL_AND_REFRAIN


def says_refrain(style: EndingStyle) -> bool:
    return style is not EndingStyle.OPEN


class StoryWritingSettings(SettingsSection):
    tone: str = Field(
        default=TONE,
        min_length=1,
        max_length=300,
        title="Tone",
        description="How the stories feel, as the writer is told: 'You write <tone>, original "
        "stories that a parent is happy to play for a small child.'",
    )
    writing_style: str = Field(
        default=WRITING_STYLE,
        min_length=1,
        max_length=500,
        title="Writing style",
        description="One requirement on how sentences sound. Change it together with the tone.",
    )
    extra_instructions: str = Field(
        default="",
        max_length=2000,
        title="Extra instructions",
        description="Anything else the writer must do. Each line becomes one requirement.",
    )
    ending_style: EndingStyle = Field(
        default=EndingStyle.MORAL_AND_REFRAIN,
        json_schema_extra=ENDING_STYLE_CHOICES,
        title="Ending",
        description="How a story ends. The ending check and translations follow it; adjust the "
        "editorial rules if they mention the ending.",
    )
    question_style: str = Field(
        default=QUESTION_STYLE,
        min_length=1,
        max_length=300,
        title="Question style",
        description="What kind of questions the writer asks children at the end.",
    )
    translation_style: str = Field(
        default=TRANSLATION_STYLE,
        min_length=1,
        max_length=300,
        title="Translation style",
        description="Words describing the language translations use, for example 'natural, "
        "simple, warm'.",
    )
    cast_per_episode: int = Field(
        default=0,
        ge=0,
        le=20,
        title="Characters per episode",
        description="How many cast members each story may use, the lead included. 0 uses all.",
    )
    lead_mode: LeadMode = Field(
        default=LeadMode.FIXED,
        json_schema_extra=LEAD_MODE_CHOICES,
        title="Lead character",
        description="The first cast member always leads, or the lead changes from episode to "
        "episode. The next cast members in order join the lead.",
    )
    enabled_checks: list[StoryCheck] = Field(
        default_factory=lambda: list(StoryCheck),
        json_schema_extra=STORY_CHECK_CHOICES,
        title="Story checks",
        description="Checks a written story must pass, or it is rewritten. Banned words and "
        "brand names are always checked.",
    )
