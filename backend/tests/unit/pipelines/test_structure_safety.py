from __future__ import annotations

from typing import Any

import pytest

from autotube.domain.pipeline_descriptors import KIDS_CONTENT
from autotube.domain.pipeline_templates import TemplateAudience
from autotube.pipelines.narrated_video.artifacts import EPISODE
from autotube.pipelines.narrated_video.engine import NarratedVideoEngine
from autotube.pipelines.narrated_video.publishing.audience_check import (
    ChildDirectedMetadataError,
    checked_audience,
)
from autotube.pipelines.narrated_video.publishing.metadata import upload_metadata
from autotube.pipelines.narrated_video.settings.series import (
    BANNED_WORDS,
    BRAND_NAMES,
    NO_HARM_RULE,
)
from autotube.pipelines.narrated_video.settings.story_choices import StoryCheck, Structure
from autotube.pipelines.narrated_video.story.checks import story_problems, translation_problems
from autotube.pipelines.narrated_video.story.prompts import story_request
from tests.fixtures.explainer_data import explainer_settings, explainer_story
from tests.fixtures.template_records import template
from tests.fixtures.template_settings import GENERAL, KIDS, defaults_for, model_for, pipeline_of

STRUCTURES = [structure.value for structure in Structure]
WEAKENED: dict[str, Any] = {
    "series": {"editorial_rules": []},
    "safety": {"banned_words": [], "brand_names": [], "audience": "general"},
    "story": {"enabled_checks": [], "age_max": 12},
}
ADDRESSED = (
    "Hello kids! Have you ever seen a bright rainbow after the rain and wondered where all of "
    "its colours come from?"
)


@pytest.mark.parametrize("structure", STRUCTURES)
def test_a_kids_template_of_any_structure_is_made_for_kids_with_the_floor(structure: str) -> None:
    descriptor = pipeline_of(KIDS, structure=structure, settings=WEAKENED).descriptor
    assert KIDS_CONTENT in descriptor.capabilities
    defaults = defaults_for(KIDS, structure=structure, settings=WEAKENED)
    assert defaults["safety"]["audience"] == "kids"
    assert defaults["safety"]["banned_words"] == BANNED_WORDS
    assert defaults["safety"]["brand_names"] == BRAND_NAMES
    assert defaults["series"]["editorial_rules"] == [NO_HARM_RULE]
    assert defaults["story"]["enabled_checks"] == [StoryCheck.READING_LEVEL.value]
    settings = model_for(KIDS, structure=structure).model_validate(defaults)
    assert upload_metadata(explainer_story(), settings, EPISODE).made_for_kids is True
    assert "children aged" in (story_request(settings, "a topic", "en").system or "")


@pytest.mark.parametrize("structure", STRUCTURES)
def test_a_general_template_of_any_structure_is_never_made_for_kids(structure: str) -> None:
    descriptor = pipeline_of(GENERAL, structure=structure).descriptor
    assert KIDS_CONTENT not in descriptor.capabilities
    settings = model_for(GENERAL, structure=structure)()
    assert upload_metadata(explainer_story(), settings, EPISODE).made_for_kids is False


def test_a_general_explainer_screens_child_directed_scripts() -> None:
    settings = explainer_settings(GENERAL)
    first, *rest = explainer_story().scenes
    addressed = explainer_story(scenes=[first.model_copy(update={"narration": ADDRESSED}), *rest])
    assert any("never address children" in item for item in story_problems(addressed, settings))
    assert any(
        "never address children" in item for item in translation_problems(addressed, settings)
    )
    assert story_problems(addressed, explainer_settings(KIDS)) == []


@pytest.mark.parametrize(
    ("action", "found"),
    [
        ("The little ones wave at the rainbow.", "never address children"),
        ("The monster lifts the rainbow.", "remove these words: monster"),
        ("A Lego tower glows under the rainbow.", "remove these brand names: Lego"),
    ],
)
def test_the_scene_action_is_screened_like_the_narration(action: str, found: str) -> None:
    first, *rest = explainer_story().scenes
    acted = explainer_story(scenes=[first.model_copy(update={"action": action}), *rest])
    settings = explainer_settings(GENERAL, safety={"banned_words": ["monster"]})
    assert any(found in item for item in story_problems(acted, settings))


@pytest.mark.parametrize("audience", [KIDS, GENERAL])
def test_explainer_upload_details_are_screened_for_a_general_audience(
    audience: TemplateAudience,
) -> None:
    metadata = {
        "title_template": {"en": "{title} for kids"},
        "tags": {"en": ["bedtime stories"]},
    }
    details = upload_metadata(
        explainer_story(), explainer_settings(audience, metadata=metadata), EPISODE
    )
    if audience is KIDS:
        assert checked_audience(details) == details
        return
    with pytest.raises(ChildDirectedMetadataError, match="never address children; remove: kids"):
        checked_audience(details)


@pytest.mark.parametrize("audience", [KIDS, GENERAL])
@pytest.mark.parametrize("structure", STRUCTURES)
def test_a_blank_template_of_every_structure_and_audience_has_no_problems(
    audience: TemplateAudience, structure: str
) -> None:
    engine = NarratedVideoEngine()
    definition = {**engine.blank(audience), "structure": structure}
    assert engine.problems(template(audience=audience, definition=definition)) == {}
