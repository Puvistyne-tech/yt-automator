from __future__ import annotations

from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.registry import installed_pipelines
from tests.fixtures.prompt_pins import stored_settings


def test_installed_descriptor_keeps_the_kids_story_type_id() -> None:
    assert [pipeline.descriptor.type_id for pipeline in installed_pipelines()] == ["kids_story"]


def test_stored_settings_validate_and_round_trip() -> None:
    loaded = KidsStorySettings.model_validate(stored_settings())
    assert KidsStorySettings.model_validate(loaded.model_dump(mode="json")) == loaded
