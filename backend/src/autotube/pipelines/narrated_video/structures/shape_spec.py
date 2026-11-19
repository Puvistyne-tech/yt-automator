from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from autotube.pipelines.narrated_video.settings.story_choices import StoryCheck, Structure
from autotube.pipelines.narrated_video.story.gates import CheckedGate, Gate
from autotube.pipelines.narrated_video.structures.castless import CASTLESS_DEFAULTS, fixed_rules
from autotube.pipelines.narrated_video.structures.paths import CAST_PATHS
from autotube.pipelines.narrated_video.structures.shape_score import structure_item
from autotube.pipelines.narrated_video.structures.spec import (
    FixedScenes,
    PlaceholderValues,
    PromptValues,
    StructureSpec,
    unseeded,
)


@dataclass(frozen=True)
class Shape:
    structure: Structure
    title: str
    wording: Mapping[str, str]
    problems: Gate
    score_title: str
    prompt_values: PromptValues
    translation_rules: tuple[str, ...]
    placeholders: tuple[str, ...]
    placeholder_values: PlaceholderValues
    leading_gates: tuple[CheckedGate, ...] = ()
    hidden_paths: tuple[str, ...] = ()
    shown_paths: tuple[str, ...] = ()
    fixed_scenes: FixedScenes | None = None


def shape_spec(shape: Shape) -> StructureSpec:
    gates = (*shape.leading_gates, (StoryCheck.STRUCTURE, shape.problems))
    return StructureSpec(
        id=shape.structure,
        title=shape.title,
        wording=shape.wording,
        prompt_values=shape.prompt_values,
        translation_rules=fixed_rules(shape.translation_rules),
        extra_gates=unseeded(gates),
        translation_gates=gates,
        score_rules=(structure_item(shape.score_title, shape.problems),),
        placeholders=shape.placeholders,
        placeholder_values=shape.placeholder_values,
        hidden_paths=(*CAST_PATHS, *shape.hidden_paths),
        shown_paths=shape.shown_paths,
        defaults_files=(CASTLESS_DEFAULTS, f"{shape.structure.value}_defaults.json"),
        fixed_scenes=shape.fixed_scenes,
    )
