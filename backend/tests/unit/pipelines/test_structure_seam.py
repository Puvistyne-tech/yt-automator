from __future__ import annotations

import pytest
from pydantic import ValidationError

from autotube.pipelines.narrated_video.engine import NarratedVideoEngine
from autotube.pipelines.narrated_video.settings.metadata import MetadataSettings
from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.settings.story_choices import Structure
from autotube.pipelines.narrated_video.structures.registry import (
    SPECS,
    metadata_placeholders,
    spec_of,
    structure_defaults,
)
from autotube.pipelines.narrated_video.template.settings_model import kids_settings_model
from tests.fixtures.prompt_pins import stored_settings
from tests.fixtures.template_records import template


def test_every_structure_has_exactly_one_spec() -> None:
    assert set(SPECS) == set(Structure)
    assert all(spec.id is structure for structure, spec in SPECS.items())


def test_the_story_spec_keeps_todays_prompts_and_bundled_fallback() -> None:
    spec = spec_of(KidsStorySettings())
    assert spec.id is Structure.STORY
    assert spec.uses_bundled is True
    assert spec.wording == {"format": "animated story", "pieces": "stories", "piece": "story"}
    assert structure_defaults(Structure.STORY) == {}
    assert {"moral", "refrain", "characters"} <= set(metadata_placeholders(Structure.STORY))


def test_settings_without_a_structure_load_as_the_story_structure() -> None:
    stored = stored_settings()
    assert "structure" not in stored["story"]
    assert KidsStorySettings.model_validate(stored).story.structure is Structure.STORY
    assert kids_settings_model().model_validate(stored).story.structure is Structure.STORY


def test_a_story_needs_a_cast() -> None:
    with pytest.raises(ValidationError, match="at least one cast member"):
        KidsStorySettings.model_validate({"cast": []})


@pytest.mark.parametrize(
    ("before", "after", "refused"),
    [
        ({}, {"structure": "story"}, False),
        ({}, {"structure": "explainer"}, True),
        ({"structure": "explainer"}, {}, True),
    ],
)
def test_the_structure_cannot_change_after_creation(
    before: dict[str, str], after: dict[str, str], refused: bool
) -> None:
    current, proposed = template(definition=before), template(definition=after)
    found = NarratedVideoEngine().revision_problems(current, proposed)
    assert ("definition.structure" in found) is refused


METADATA_FIELDS = ["title_template", "short_title_template", "description_template"]


@pytest.mark.parametrize("field", METADATA_FIELDS)
def test_every_metadata_field_names_every_structures_own_placeholders(field: str) -> None:
    description = MetadataSettings.model_fields[field].description or ""
    named = {name for spec in SPECS.values() for name in spec.placeholders}
    assert [name for name in sorted(named) if f"{{{name}}}" not in description] == []


def test_every_structure_has_a_short_title() -> None:
    assert [spec.title for spec in SPECS.values()] == [
        "Story with a recurring cast",
        "Explainer",
        "List",
        "Countdown",
        "Quiz",
    ]
