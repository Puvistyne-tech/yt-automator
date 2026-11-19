from __future__ import annotations

from collections.abc import Callable, Mapping
from enum import StrEnum

from pydantic.config import JsonDict

from autotube.domain.pipeline_templates import TemplateAudience
from autotube.domain.video_look import SubtitlePosition, Transition, VideoQuality
from autotube.pipelines.narrated_video.languages import LANGUAGE_NAMES
from autotube.pipelines.narrated_video.settings.base import Placement

ChoiceSchema = Callable[[JsonDict], None]


def titled_choices(titles: Mapping[str, str]) -> ChoiceSchema:
    def apply(schema: JsonDict) -> None:
        schema.pop("$ref", None)
        schema.pop("enum", None)
        schema["type"] = "string"
        schema["oneOf"] = [{"const": value, "title": title} for value, title in titles.items()]

    return apply


def enum_choices(enum: type[StrEnum], titles: Mapping[str, str]) -> ChoiceSchema:
    members = {member.value for member in enum}
    if set(titles) != members:
        missing, extra = sorted(members - set(titles)), sorted(set(titles) - members)
        raise ValueError(f"{enum.__name__} titles differ; missing {missing}, extra {extra}")
    return titled_choices(titles)


def checkbox_choices(enum: type[StrEnum], titles: Mapping[str, str]) -> ChoiceSchema:
    item_choices = enum_choices(enum, titles)

    def apply(schema: JsonDict) -> None:
        items: JsonDict = {}
        item_choices(items)
        schema["items"] = items
        schema["uniqueItems"] = True

    return apply


LANGUAGE_CHOICES = titled_choices(LANGUAGE_NAMES)
STORY_SOURCE_CHOICES = titled_choices(
    {
        "llm_with_fallback": "Language model, bundled story if it fails",
        "bundled_only": "Bundled stories only",
    }
)
THEME_MODE_CHOICES = titled_choices(
    {"rotate": "Rotate through the themes", "fixed": "Always the fixed theme"}
)
AUDIENCE_CHOICES = enum_choices(TemplateAudience, {"kids": "Kids", "general": "General audience"})
READING_LEVEL_CHOICES = titled_choices(
    {
        "toddler": "Toddler",
        "preschool": "Preschool",
        "early_reader": "Early reader",
        "general": "General",
    }
)
CAMERA_MOVE_CHOICES = titled_choices(
    {
        "push_in": "Push in",
        "pull_out": "Pull out",
        "pan_left": "Pan left",
        "pan_right": "Pan right",
        "rise": "Rise",
        "still": "Hold still",
    }
)
SHORT_ART_CHOICES = titled_choices(
    {"native": "Draw a new vertical picture", "crop": "Crop the wide picture"}
)
CORNER_TITLES = {
    "top_left": "Top left",
    "top_right": "Top right",
    "bottom_left": "Bottom left",
    "bottom_right": "Bottom right",
}
EDGE_TITLES = {"top": "Top", "bottom": "Bottom"}
CORNER_CHOICES = titled_choices(CORNER_TITLES)
EDGE_CHOICES = titled_choices(EDGE_TITLES)
PLACEMENT_CHOICES = enum_choices(Placement, {**EDGE_TITLES, "center": "Centre", **CORNER_TITLES})
SUBTITLE_POSITION_CHOICES = enum_choices(
    SubtitlePosition, {"bottom": "Bottom", "middle": "Middle", "top": "Top"}
)
TRANSITION_CHOICES = enum_choices(
    Transition,
    {"cut": "Cut", "crossfade": "Crossfade", "fade_through_black": "Fade through black"},
)
VIDEO_QUALITY_CHOICES = enum_choices(
    VideoQuality,
    {
        "draft": "Draft: small files, softer picture",
        "standard": "Standard: the media provider's quality",
        "high": "High: sharper, larger files",
        "best": "Best: sharpest, largest files",
    },
)
CATEGORY_CHOICES = titled_choices(
    {"1": "Film & Animation", "24": "Entertainment", "27": "Education"}
)
LANDSCAPE_CHOICES = titled_choices(
    {
        "640x360": "360p preview (640×360)",
        "1280x720": "720p HD (1280×720)",
        "1920x1080": "1080p Full HD (1920×1080)",
        "3840x2160": "4K Ultra HD (3840×2160)",
    }
)
PORTRAIT_CHOICES = titled_choices(
    {
        "360x640": "360p preview (360×640)",
        "720x1280": "720p HD (720×1280)",
        "1080x1920": "1080p Full HD (1080×1920)",
    }
)
SCENE_SELECTION_CHOICES = titled_choices(
    {"auto": "Best scenes, picked automatically", "first_n": "First scenes, in story order"}
)
