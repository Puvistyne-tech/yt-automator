from __future__ import annotations

import pytest

from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.story.child_terms import child_terms_in
from tests.fixtures.prompt_pins import (
    GENERAL_FOLDER,
    pinned_prompt,
    rendered_prompts,
    stored_settings,
)
from tests.fixtures.template_settings import GENERAL, general_story, model_for

PROMPT_NAMES = sorted(rendered_prompts(KidsStorySettings()))


def general_prompts() -> dict[str, str]:
    return rendered_prompts(model_for(GENERAL)(), general_story())


@pytest.mark.parametrize("name", PROMPT_NAMES)
def test_default_settings_render_the_pinned_prompts(name: str) -> None:
    assert rendered_prompts(KidsStorySettings())[name] == pinned_prompt(name)


@pytest.mark.parametrize("name", PROMPT_NAMES)
def test_general_defaults_render_the_pinned_general_prompts(name: str) -> None:
    rendered = general_prompts()[name]
    assert rendered == pinned_prompt(name, GENERAL_FOLDER)
    assert child_terms_in(rendered) == []


def test_stored_settings_without_new_fields_load_as_the_defaults() -> None:
    loaded = KidsStorySettings.model_validate(stored_settings())
    assert loaded == KidsStorySettings()
    assert KidsStorySettings.model_validate(loaded.model_dump(mode="json")) == loaded
