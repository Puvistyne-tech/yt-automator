from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from autotube.pipelines.narrated_video.settings.choices import READING_LEVEL_CHOICES
from autotube.pipelines.narrated_video.settings.story_controls import StoryWritingSettings

OLDEST_CHILD = 12
OLDEST_AGE = 99


class ReadingLevel(StrEnum):
    TODDLER = "toddler"
    PRESCHOOL = "preschool"
    EARLY_READER = "early_reader"
    GENERAL = "general"


class StoryAudienceSettings(StoryWritingSettings):
    age_min: int = Field(
        default=3,
        ge=1,
        le=OLDEST_AGE,
        title="Youngest age",
        description="Youngest viewer, in years.",
    )
    age_max: int = Field(
        default=7,
        ge=1,
        le=OLDEST_AGE,
        title="Oldest age",
        description="Oldest viewer, in years. A kids video is for children aged "
        f"{OLDEST_CHILD} or under.",
    )
    reading_level: ReadingLevel = Field(
        default=ReadingLevel.PRESCHOOL,
        json_schema_extra=READING_LEVEL_CHOICES,
        title="Reading level",
        description="How simple the language must be. General is for teenagers and adults only.",
    )


def kids_audience_problem(story: StoryAudienceSettings) -> str:
    if story.age_max > OLDEST_CHILD:
        return f"a kids video is for children aged {OLDEST_CHILD} or under"
    if story.reading_level is ReadingLevel.GENERAL:
        return "a kids video needs a kids reading level, not general"
    return ""
