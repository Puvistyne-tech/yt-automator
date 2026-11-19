from __future__ import annotations

import pytest

from autotube.domain.pipeline_templates import TemplateAudience
from autotube.pipelines.narrated_video.settings.story_choices import Structure
from autotube.pipelines.narrated_video.story.model import StoryDraft, StoryScene
from autotube.pipelines.narrated_video.story.prompt_parts import (
    GENERAL_ACTION_EXAMPLE,
    KIDS_ACTION_EXAMPLE,
)
from autotube.pipelines.narrated_video.story.prompts import story_request
from tests.fixtures.kids_data import draft_dict
from tests.fixtures.template_settings import GENERAL, KIDS, model_for

ACTION_START = "- For each scene, also write `action`: one short present-tense sentence"
ACTION_END = "Do not mention the camera, dialogue, sounds, text or more than one event."


def test_a_stored_scene_without_an_action_still_validates() -> None:
    scene = StoryScene.model_validate({"narration": "Hello.", "visual": "a pond"})
    assert scene.action == ""
    draft = StoryDraft.model_validate(draft_dict())
    assert all(item.action == "" for item in draft.scenes)


def test_the_writer_schema_describes_the_action() -> None:
    properties = StoryScene.model_json_schema()["properties"]
    assert properties["action"]["description"].startswith("One short present-tense sentence")


@pytest.mark.parametrize("structure", list(Structure))
@pytest.mark.parametrize(
    ("audience", "example", "other"),
    [(KIDS, KIDS_ACTION_EXAMPLE, GENERAL_ACTION_EXAMPLE), (GENERAL, GENERAL_ACTION_EXAMPLE, "fox")],
)
def test_every_script_prompt_asks_for_an_action_per_scene(
    structure: Structure, audience: TemplateAudience, example: str, other: str
) -> None:
    settings = model_for(audience, structure=structure.value)()
    prompt = story_request(settings, "a topic", "en").prompt
    [line] = [text for text in prompt.splitlines() if text.startswith(ACTION_START)]
    assert f"(for example: '{example}')" in line and line.endswith(ACTION_END)
    assert other not in prompt
    assert '"action": "..."' in prompt
