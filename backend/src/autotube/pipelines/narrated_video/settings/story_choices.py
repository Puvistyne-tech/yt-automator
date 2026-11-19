from __future__ import annotations

from enum import StrEnum

from autotube.pipelines.narrated_video.settings.choices import checkbox_choices, enum_choices


class EndingStyle(StrEnum):
    MORAL_AND_REFRAIN = "moral_and_refrain"
    REFRAIN_ONLY = "refrain_only"
    OPEN = "open"


class LeadMode(StrEnum):
    FIXED = "fixed"
    PER_EPISODE = "per_episode"


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


ENDING_STYLE_CHOICES = enum_choices(
    EndingStyle,
    {
        "moral_and_refrain": "The moral, then the refrain",
        "refrain_only": "The refrain only",
        "open": "An open ending, no moral or refrain",
    },
)
LEAD_MODE_CHOICES = enum_choices(
    LeadMode,
    {
        "fixed": "The first cast member always leads",
        "per_episode": "A lead picked for each episode",
    },
)
STORY_CHECK_CHOICES = checkbox_choices(
    StoryCheck,
    {
        "scene_count": "Number of scenes",
        "words_per_scene": "Words per scene",
        "duration": "Episode length",
        "ending": "Ending (moral and refrain)",
        "reading_level": "Reading level",
        "cast": "Only the episode's characters",
    },
)
