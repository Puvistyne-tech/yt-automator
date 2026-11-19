from __future__ import annotations

import pytest

from autotube.domain.pipeline_templates import TemplateAudience
from autotube.pipelines.narrated_video.publishing.audience_check import (
    ChildDirectedMetadataError,
    checked_audience,
)
from autotube.pipelines.narrated_video.publishing.metadata import UploadMetadata, upload_metadata
from autotube.pipelines.narrated_video.template.settings_model import kids_settings_model
from tests.fixtures.prompt_pins import stored_settings
from tests.fixtures.template_settings import GENERAL, KIDS, general_story, model_for

CLEAN = {
    "title": "A long way home",
    "description": "A story about a second chance.",
    "tags": ["short stories"],
    "hashtags": ["#Stories"],
    "category_id": "1",
    "default_language": "en",
    "playlist_title": "Story Time",
}


def metadata(made_for_kids: bool, **changes: object) -> UploadMetadata:
    return UploadMetadata.model_validate({**CLEAN, "made_for_kids": made_for_kids, **changes})


@pytest.mark.parametrize(
    "changes",
    [
        {"title": "A long way home for KIDS"},
        {"description": "Bedtime stories: a second chance."},
        {"tags": ["short stories", "kids stories"]},
        {"hashtags": ["#KidsStories"]},
        {"playlist_title": "குழந்தைகள் கதைகள்", "default_language": "ta"},
    ],
)
def test_general_upload_details_with_a_child_term_are_refused(changes: dict[str, object]) -> None:
    with pytest.raises(ChildDirectedMetadataError, match="never address children"):
        checked_audience(metadata(False, **changes))
    kids = metadata(True, **changes)
    assert checked_audience(kids) is kids


def test_clean_general_upload_details_pass() -> None:
    clean = metadata(False, tags=["kidney health"])
    assert checked_audience(clean) is clean


@pytest.mark.parametrize(
    ("audience", "stored", "made_for_kids"),
    [
        (KIDS, {"safety": {"audience": "general"}}, True),
        (GENERAL, {"safety": {"audience": "kids"}}, False),
    ],
)
def test_stored_settings_cannot_change_the_template_audience(
    audience: TemplateAudience, stored: dict[str, object], made_for_kids: bool
) -> None:
    model = model_for(audience)
    loaded = model.model_validate(stored)
    assert loaded.safety.audience is audience
    reloaded = model.model_validate(loaded.model_dump(mode="json"))
    assert upload_metadata(general_story(), reloaded, "episode").made_for_kids is made_for_kids


def test_legacy_kids_story_settings_load_as_kids() -> None:
    assert "audience" not in stored_settings().get("safety", {})
    loaded = kids_settings_model().model_validate(stored_settings())
    assert loaded.safety.audience is KIDS
    assert upload_metadata(general_story(), loaded, "episode").made_for_kids is True
