from __future__ import annotations

from autotube.domain.model_base import JsonObject
from autotube.pipelines.narrated_video.publishing.placeholder_values import COMMON_PLACEHOLDERS
from autotube.pipelines.narrated_video.resources import resource_json
from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.settings.story_choices import Structure
from autotube.pipelines.narrated_video.structures.explainer import EXPLAINER_SPEC
from autotube.pipelines.narrated_video.structures.numbered import COUNTDOWN_SPEC, LIST_SPEC
from autotube.pipelines.narrated_video.structures.quiz import QUIZ_SPEC
from autotube.pipelines.narrated_video.structures.spec import StructureSpec
from autotube.pipelines.narrated_video.structures.story import STORY_SPEC

FOLDER = "structures"
SPECS: dict[Structure, StructureSpec] = {
    spec.id: spec for spec in (STORY_SPEC, EXPLAINER_SPEC, LIST_SPEC, COUNTDOWN_SPEC, QUIZ_SPEC)
}


def structure_spec(structure: Structure) -> StructureSpec:
    return SPECS[structure]


def spec_of(settings: KidsStorySettings) -> StructureSpec:
    return structure_spec(settings.story.structure)


def metadata_placeholders(structure: Structure) -> tuple[str, ...]:
    return (*COMMON_PLACEHOLDERS, *structure_spec(structure).placeholders)


def defaults_file(name: str) -> JsonObject:
    loaded = resource_json(FOLDER, name)
    return loaded if isinstance(loaded, dict) else {}


def structure_defaults(structure: Structure) -> tuple[JsonObject, ...]:
    return tuple(defaults_file(name) for name in structure_spec(structure).defaults_files)
