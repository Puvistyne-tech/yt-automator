from __future__ import annotations

from pydantic import BaseModel, JsonValue

from autotube.domain.model_base import JsonObject
from autotube.pipelines.narrated_video.structures.registry import structure_spec
from autotube.pipelines.narrated_video.template.definition import Length, NarratedDefinition

LENGTH_PRESETS: dict[Length, JsonObject] = {
    Length.SHORT: {
        "target_duration_seconds": 60,
        "duration_tolerance_seconds": 15,
        "scene_count_min": 4,
        "scene_count_max": 6,
    },
    Length.STANDARD: {},
    Length.LONG: {
        "target_duration_seconds": 300,
        "duration_tolerance_seconds": 45,
        "scene_count_min": 14,
        "scene_count_max": 18,
    },
}
FIXED_SCENE_PRESETS: dict[Length, JsonObject] = {
    Length.SHORT: {
        "words_per_scene_min": {"en": 10, "ta": 6},
        "words_per_scene_max": {"en": 20, "ta": 14},
    },
    Length.STANDARD: {},
    Length.LONG: {
        "words_per_scene_min": {"en": 40, "ta": 30},
        "words_per_scene_max": {"en": 80, "ta": 60},
    },
}
BRIEF_PREFIX = "Every video is about: "


def length_preset(definition: NarratedDefinition) -> JsonObject:
    fixed = structure_spec(definition.structure).fixed_scenes is not None
    return (FIXED_SCENE_PRESETS if fixed else LENGTH_PRESETS)[definition.length]


def filled(value: JsonValue) -> bool:
    return value not in ("", [], {}, None)


def sparse(values: dict[str, JsonValue]) -> JsonObject:
    return {key: value for key, value in values.items() if filled(value)}


def per_language(value: BaseModel) -> JsonObject:
    return sparse(value.model_dump(mode="json"))


def story_values(definition: NarratedDefinition) -> JsonObject:
    brief = definition.brief.strip()
    return sparse(
        {
            **length_preset(definition),
            "tone": definition.tone.strip(),
            "themes": [topic for topic in definition.topics if topic.strip()],
            "extra_instructions": f"{BRIEF_PREFIX}{brief}" if brief else "",
        }
    )


def metadata_values(definition: NarratedDefinition) -> JsonObject:
    return sparse(
        {
            "title_template": per_language(definition.title_template),
            "short_title_template": per_language(definition.short_title_template),
            "description_template": per_language(definition.description_template),
            "tags": per_language(definition.tags),
            "hashtags": per_language(definition.hashtags),
            "category": definition.category.value,
        }
    )


def definition_settings(definition: NarratedDefinition) -> JsonObject:
    return sparse(
        {
            "story": story_values(definition),
            "look": sparse({"visual_style": definition.visual_style}),
            "music": sparse({"mood_prompt": definition.music_mood.strip()}),
            "metadata": metadata_values(definition),
        }
    )
