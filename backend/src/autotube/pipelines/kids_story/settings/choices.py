from __future__ import annotations

from collections.abc import Callable, Mapping
from enum import StrEnum

from pydantic.config import JsonDict

from autotube.pipelines.kids_story.languages import LANGUAGE_NAMES

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
READING_LEVEL_CHOICES = titled_choices(
    {"toddler": "Toddler", "preschool": "Preschool", "early_reader": "Early reader"}
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
CORNER_CHOICES = titled_choices(
    {
        "top_left": "Top left",
        "top_right": "Top right",
        "bottom_left": "Bottom left",
        "bottom_right": "Bottom right",
    }
)
EDGE_CHOICES = titled_choices({"top": "Top", "bottom": "Bottom"})
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
