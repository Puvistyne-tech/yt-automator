from __future__ import annotations

from autotube.domain.pipeline_templates import TemplateAudience
from autotube.pipelines.narrated_video.settings.story_choices import Structure
from autotube.pipelines.narrated_video.structures.registry import structure_spec
from autotube.pipelines.narrated_video.template.audience import (
    SOURCE_PATH,
    Pins,
    audience_pins,
    llm_only_pins,
)


def structure_pins(structure: Structure) -> Pins:
    llm_only = {} if structure_spec(structure).uses_bundled else llm_only_pins()
    return {"story": {"structure": structure.value, **llm_only}}


def template_pins(audience: TemplateAudience, structure: Structure) -> Pins:
    pins = audience_pins(audience)
    for section, values in structure_pins(structure).items():
        pins[section] = {**pins.get(section, {}), **values}
    return pins


def structure_hidden_paths(structure: Structure) -> tuple[str, ...]:
    spec = structure_spec(structure)
    fixed = () if spec.uses_bundled else (SOURCE_PATH,)
    return (*spec.hidden_paths, *fixed)
