from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from autotube.pipelines.narrated_video.scoring.inputs import ScoreRule
from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.settings.story_choices import Structure
from autotube.pipelines.narrated_video.story.gates import CheckedGate
from autotube.pipelines.narrated_video.story.model import Story
from autotube.pipelines.narrated_video.story.repair_text import Repaired

PromptValues = Callable[[KidsStorySettings, str, str], dict[str, str]]
TranslationRules = Callable[[KidsStorySettings, str], str]
PlaceholderValues = Callable[[Story, KidsStorySettings], dict[str, str]]
SeededGates = Callable[[str], tuple[CheckedGate, ...]]
FixedScenes = Callable[[KidsStorySettings], int]
MoralRule = Callable[[KidsStorySettings], bool]
Schema = dict[str, Any]
SceneShapes = Callable[[KidsStorySettings], list[Schema]]
Repair = Callable[[Story, KidsStorySettings], Repaired]


def no_moral(settings: KidsStorySettings) -> bool:  # noqa: ARG001
    return False


def always_moral(settings: KidsStorySettings) -> bool:  # noqa: ARG001
    return True


def unseeded(gates: tuple[CheckedGate, ...]) -> SeededGates:
    def chosen(seed: str) -> tuple[CheckedGate, ...]:  # noqa: ARG001
        return gates

    return chosen


@dataclass(frozen=True)
class StructureSpec:
    id: Structure
    title: str
    wording: Mapping[str, str]
    prompt_values: PromptValues
    translation_rules: TranslationRules
    extra_gates: SeededGates
    translation_gates: tuple[CheckedGate, ...]
    score_rules: tuple[ScoreRule, ...]
    placeholders: tuple[str, ...]
    placeholder_values: PlaceholderValues
    uses_bundled: bool = False
    basic_paths: tuple[str, ...] = ()
    hidden_paths: tuple[str, ...] = ()
    shown_paths: tuple[str, ...] = ()
    defaults_files: tuple[str, ...] = ()
    fixed_scenes: FixedScenes | None = None
    moral_required: MoralRule = no_moral
    scene_shapes: SceneShapes | None = None
    repairs: tuple[Repair, ...] = ()
