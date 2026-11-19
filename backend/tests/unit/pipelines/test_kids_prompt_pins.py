from __future__ import annotations

import pytest

from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from tests.fixtures.prompt_pins import pinned_prompt, rendered_prompts, stored_settings

PROMPT_NAMES = sorted(rendered_prompts(KidsStorySettings()))


@pytest.mark.parametrize("name", PROMPT_NAMES)
def test_default_settings_render_the_pinned_prompts(name: str) -> None:
    assert rendered_prompts(KidsStorySettings())[name] == pinned_prompt(name)


def test_stored_settings_without_new_fields_load_as_the_defaults() -> None:
    assert KidsStorySettings.model_validate(stored_settings()) == KidsStorySettings()
