from __future__ import annotations

import pytest
from pydantic import ValidationError

from autotube.pipelines.narrated_video.engine import NarratedVideoEngine
from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.settings.story_choices import Structure
from autotube.pipelines.narrated_video.structures.registry import (
    SPECS,
    metadata_placeholders,
    spec_of,
    structure_defaults,
)
from autotube.pipelines.narrated_video.template.settings_model import kids_settings_model
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


def test_settings_default_to_the_story_structure() -> None:
    assert KidsStorySettings().story.structure is Structure.STORY
    assert kids_settings_model()().story.structure is Structure.STORY


def test_a_story_needs_a_cast() -> None:
    with pytest.raises(ValidationError, match="at least one cast member"):
        KidsStorySettings.model_validate({"cast": []})


@pytest.mark.parametrize(
    ("before", "after", "refused"),
    [
        ({}, {"structure": "story"}, False),
        ({"structure": "story"}, {"brief": "planets"}, False),
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
