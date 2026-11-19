from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from autotube.pipelines.narrated_video.scoring.inputs import ScoreRule
from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.settings.story_choices import Structure
from autotube.pipelines.narrated_video.story.gates import (
    CheckedGate,
    SceneRange,
    configured_scene_range,
)
from autotube.pipelines.narrated_video.story.model import Story

PromptValues = Callable[[KidsStorySettings, str, str], dict[str, str]]
TranslationRules = Callable[[KidsStorySettings, str], str]
PlaceholderValues = Callable[[Story, KidsStorySettings], dict[str, str]]
SeededGates = Callable[[str], tuple[CheckedGate, ...]]


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
    defaults_file: str = ""
    scene_range: SceneRange = configured_scene_range
