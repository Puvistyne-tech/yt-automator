from __future__ import annotations

from typing import Any

import pytest

from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.story.answer_schema import draft_schema, text_schema
from autotube.pipelines.narrated_video.story.model import StoryDraft, StoryText
from autotube.pipelines.narrated_video.story.prompts import story_request, translation_request
from tests.fixtures.explainer_data import TAKEAWAY_ENDING, explainer_draft, explainer_settings
from tests.fixtures.kids_data import draft_dict, story
from tests.fixtures.list_data import list_settings, list_story
from tests.fixtures.mac_runs import mac_settings
from tests.fixtures.quiz_data import quiz_settings, quiz_story
from tests.fixtures.schema_fit import misfits
from tests.fixtures.shaped_scripts import shaped_draft
from tests.fixtures.template_settings import GENERAL

CASTLESS = {
    "list": list_settings(GENERAL),
    "countdown": list_settings(GENERAL, "countdown"),
    "quiz": quiz_settings(GENERAL),
}


def dumped(draft: dict[str, Any]) -> dict[str, Any]:
    return StoryDraft.model_validate(draft).model_dump(mode="json")


def moral_of(schema: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    return "moral" in schema["required"], schema["properties"]["moral"]


def test_a_kids_story_must_send_a_moral_and_its_scene_range() -> None:
    schema = draft_schema(mac_settings())
    assert moral_of(schema) == (True, {"type": "string", "minLength": 1, "title": "Moral"})
    scenes = schema["properties"]["scenes"]
    assert (scenes["minItems"], scenes["maxItems"]) == (4, 6) and "scenes" in schema["required"]
    assert misfits(schema, dumped({**draft_dict(), "moral": ""}))
    assert misfits(draft_schema(KidsStorySettings()), dumped(draft_dict())) == []


def test_the_story_request_and_translation_send_the_shaped_schemas() -> None:
    settings = mac_settings()
    assert story_request(settings, "sharing", "en").json_schema == draft_schema(settings)
    request = translation_request(settings, story(), "en", "ta")
    assert request.json_schema == text_schema(settings, story())
    assert request.json_schema["title"] == "StoryText"


@pytest.mark.parametrize("sections", [{}, {"story": TAKEAWAY_ENDING}])
def test_an_explainer_draft_fits_its_schema_with_or_without_a_takeaway(
    sections: dict[str, Any],
) -> None:
    schema = draft_schema(explainer_settings(GENERAL, **sections))
    assert misfits(schema, dumped(explainer_draft())) == []


@pytest.mark.parametrize("settings", list(CASTLESS.values()), ids=list(CASTLESS))
def test_castless_formats_shape_every_scene_and_keep_the_moral_optional(
    settings: KidsStorySettings,
) -> None:
    schema = draft_schema(settings)
    assert not moral_of(schema)[0] and moral_of(schema)[1]["default"] == ""
    assert misfits(schema, dumped(shaped_draft(settings))) == []
    scenes = schema["properties"]["scenes"]
    assert scenes["minItems"] == scenes["maxItems"] == len(scenes["prefixItems"])


def test_a_list_fixes_each_item_number_in_order() -> None:
    settings = list_settings(GENERAL, "countdown")
    items = draft_schema(settings)["properties"]["scenes"]["prefixItems"]
    numbers = [item["properties"]["number"] for item in items]
    count = settings.story.item_count
    assert numbers[1:-1] == [{"type": "integer", "const": n} for n in range(count, 0, -1)]
    assert numbers[0] == numbers[-1] == {"type": "null"}
    swapped = list_story(countdown=True).model_dump(mode="json")
    swapped["scenes"][1]["number"], swapped["scenes"][2]["number"] = 1, 2
    assert misfits(draft_schema(settings), swapped)


def test_a_quiz_asks_then_reveals_with_the_set_number_of_choices() -> None:
    settings = quiz_settings(GENERAL, story={"answer_choices": 3})
    items = draft_schema(settings)["properties"]["scenes"]["prefixItems"]
    ask, reveal = items[1]["properties"], items[2]["properties"]
    assert ask["question"]["minLength"] == 1 and ask["choices"]["minItems"] == 3
    assert reveal["answer"]["minLength"] == 1 and reveal["question"]["maxLength"] == 0
    assert misfits(draft_schema(settings), quiz_story(choices=True).model_dump(mode="json")) == []
    assert misfits(draft_schema(settings), quiz_story().model_dump(mode="json"))


def test_a_translation_keeps_every_scene_and_its_labels() -> None:
    script = list_story()
    schema = text_schema(list_settings(GENERAL), script)
    narrations = schema["properties"]["narrations"]
    assert narrations["minItems"] == narrations["maxItems"] == len(script.scenes)
    assert "scene_labels" in schema["required"] and "moral" not in schema["required"]
    story_schema = text_schema(KidsStorySettings(), story())
    assert "scene_labels" not in story_schema["required"] and "moral" in story_schema["required"]
    assert StoryText.model_json_schema()["required"] == ["title", "narrations"]
