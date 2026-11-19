from __future__ import annotations

import pytest

from autotube.domain.pipeline_templates import TemplateAudience
from autotube.pipelines.narrated_video.artifacts import EPISODE, SHORT
from autotube.pipelines.narrated_video.publishing.audience_check import (
    ChildDirectedMetadataError,
    checked_audience,
    metadata_texts,
)
from autotube.pipelines.narrated_video.publishing.metadata import upload_metadata
from autotube.pipelines.narrated_video.story.checks import story_problems
from autotube.pipelines.narrated_video.story.child_terms import child_terms_in, child_terms_in_any
from tests.fixtures.structure_writers import SCRIPTED_STORIES
from tests.fixtures.template_settings import GENERAL, KIDS, defaults_for, model_for

STRUCTURES = list(SCRIPTED_STORIES)
ADDRESSED = {"title_template": {"en": "{title} for kids"}, "tags": {"en": ["bedtime stories"]}}


@pytest.mark.parametrize("structure", STRUCTURES)
@pytest.mark.parametrize("variant", [EPISODE, SHORT])
def test_general_default_upload_details_are_free_of_child_terms(
    structure: str, variant: str
) -> None:
    settings = model_for(GENERAL, structure=structure)()
    details = upload_metadata(SCRIPTED_STORIES[structure](), settings, variant)
    assert details.made_for_kids is False
    assert child_terms_in_any(metadata_texts(details)) == []
    assert "{" not in details.title + details.description
    defaults = defaults_for(GENERAL, structure=structure)
    assert child_terms_in(defaults["story"]["question_style"]) == []


@pytest.mark.parametrize("structure", STRUCTURES)
@pytest.mark.parametrize("audience", [KIDS, GENERAL])
def test_upload_details_are_screened_for_a_general_audience(
    structure: str, audience: TemplateAudience
) -> None:
    settings = model_for(audience, structure=structure).model_validate({"metadata": ADDRESSED})
    details = upload_metadata(SCRIPTED_STORIES[structure](), settings, EPISODE)
    if audience is KIDS:
        assert details.made_for_kids is True and checked_audience(details) == details
        return
    with pytest.raises(ChildDirectedMetadataError, match="never address children"):
        checked_audience(details)


@pytest.mark.parametrize("structure", STRUCTURES)
def test_a_general_script_that_addresses_children_is_rejected(structure: str) -> None:
    sample = SCRIPTED_STORIES[structure]()
    first, *rest = sample.scenes
    addressed = first.model_copy(update={"narration": f"Hello kids! {first.narration}"})
    changed = sample.model_copy(update={"scenes": [addressed, *rest]})
    general = model_for(GENERAL, structure=structure)()
    assert any("never address children" in item for item in story_problems(changed, general))
    assert story_problems(sample, general) == []
    assert story_problems(changed, model_for(KIDS, structure=structure)()) == []
