from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from autotube.pipelines.narrated_video.scoring.inputs import ScoreRule
from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.settings.story_choices import Structure
from autotube.pipelines.narrated_video.story.gates import CheckedGate
from autotube.pipelines.narrated_video.story.model import Story

PromptValues = Callable[[KidsStorySettings, str, str], dict[str, str]]
TranslationRules = Callable[[KidsStorySettings, str], str]
PlaceholderValues = Callable[[Story, KidsStorySettings], dict[str, str]]
SeededGates = Callable[[str], tuple[CheckedGate, ...]]


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
    defaults_file: str = ""
