from __future__ import annotations

from autotube.domain.pipeline_templates import TemplateAudience
from autotube.pipelines.narrated_video.settings.story import StorySource
from autotube.pipelines.narrated_video.settings.story_choices import Structure
from autotube.pipelines.narrated_video.structures.registry import structure_spec
from autotube.pipelines.narrated_video.template.audience import SOURCE_PATH, Pins, audience_pins


def structure_pins(structure: Structure) -> Pins:
    story = {"structure": structure.value}
    if not structure_spec(structure).uses_bundled:
        story["source"] = StorySource.LLM_WITH_FALLBACK.value
    return {"story": story}


def template_pins(audience: TemplateAudience, structure: Structure) -> Pins:
    pins = audience_pins(audience)
    for section, values in structure_pins(structure).items():
        pins[section] = {**pins.get(section, {}), **values}
    return pins


def structure_hidden_paths(structure: Structure) -> tuple[str, ...]:
    spec = structure_spec(structure)
    fixed = () if spec.uses_bundled else (SOURCE_PATH,)
    return (*spec.hidden_paths, *fixed)
