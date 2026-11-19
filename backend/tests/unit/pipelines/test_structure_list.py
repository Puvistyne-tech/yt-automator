from __future__ import annotations

from dataclasses import dataclass

import pytest

from autotube.domain.pipeline_templates import TemplateAudience
from autotube.pipelines.narrated_video.publishing.templates import template_values
from autotube.pipelines.narrated_video.settings.story import StorySource
from autotube.pipelines.narrated_video.settings.story_choices import StoryCheck, Structure
from autotube.pipelines.narrated_video.story.checks import story_problems, translation_problems
from autotube.pipelines.narrated_video.story.model import Story
from autotube.pipelines.narrated_video.story.prompts import story_request, translation_request
from tests.fixtures.list_data import list_settings, list_story, tamil_list, with_scene
from tests.fixtures.template_settings import GENERAL, KIDS, defaults_for


@dataclass(frozen=True)
class Numbered:
    structure: str
    countdown: bool
    format: str
    first_items: str

    def order(self, count: int) -> str:
        if self.countdown:
            return f"number the items from {count} down to 1, so the last item is number 1"
        return f"number the items from 1 up to {count}, in that order"

    def story(self) -> Story:
        return list_story(countdown=self.countdown)


LIST = Numbered("list", False, "short numbered list videos", "Bees dance to talk, Bees have ")
COUNTDOWN = Numbered("countdown", True, "short countdown videos", "Honey keeps for years, Wings ")
NUMBERED = [pytest.param(LIST, id="list"), pytest.param(COUNTDOWN, id="countdown")]
AUDIENCES = [KIDS, GENERAL]
UNFRAMED = "open with an intro scene and end with a closing scene, both without a number"


@pytest.mark.parametrize("audience", AUDIENCES)
@pytest.mark.parametrize("case", NUMBERED)
def test_a_numbered_model_pins_its_structure_and_the_writer_source(
    case: Numbered, audience: TemplateAudience
) -> None:
    pinned = {"structure": "story", "source": "bundled_only"}
    loaded = list_settings(audience, case.structure, story=pinned)
    assert loaded.story.structure is Structure(case.structure)
    assert loaded.story.source is StorySource.LLM_WITH_FALLBACK
    assert loaded.cast == [] and loaded.story.item_count == 7


@pytest.mark.parametrize("audience", AUDIENCES)
@pytest.mark.parametrize("case", NUMBERED)
def test_a_written_script_and_its_translation_pass_their_checks(
    case: Numbered, audience: TemplateAudience
) -> None:
    settings = list_settings(audience, case.structure)
    assert story_problems(case.story(), settings) == []
    tamil = tamil_list(countdown=case.countdown)
    assert translation_problems(tamil, settings) == []
    assert tamil.scenes[1].number == case.story().scenes[1].number
    assert tamil.scenes[1].heading != case.story().scenes[1].heading


@pytest.mark.parametrize("case", NUMBERED)
def test_numbering_headings_and_framing_are_checked(case: Numbered) -> None:
    settings = list_settings(KIDS, case.structure)
    sample = case.story()
    first, second = sample.scenes[1].number, sample.scenes[2].number
    swapped = with_scene(with_scene(sample, 1, number=second), 2, number=first)
    assert story_problems(swapped, settings) == [case.order(7)]
    doubled = with_scene(sample, 2, number=first)
    assert story_problems(doubled, settings) == [case.order(7)]
    repeated = with_scene(sample, 2, heading=sample.scenes[1].heading.upper())
    assert story_problems(repeated, settings) == ["give every item its own heading"]
    blank = with_scene(sample, 3, heading=" ")
    assert story_problems(blank, settings) == ["give every item a short heading"]


@pytest.mark.parametrize("case", NUMBERED)
def test_a_missing_item_or_a_numbered_intro_is_reported(case: Numbered) -> None:
    settings = list_settings(KIDS, case.structure)
    scenes = case.story().scenes
    short = list_story(case.countdown, scenes=[*scenes[:2], *scenes[3:]])
    assert story_problems(short, settings) == [
        "use exactly 9 scenes, not 8",
        "write exactly 7 numbered items, not 6",
        case.order(6),
    ]
    framed = with_scene(case.story(), 0, number=8)
    found = story_problems(framed, settings)
    assert found[:2] == [UNFRAMED, "write exactly 7 numbered items, not 8"]
    lone = list_story(case.countdown, scenes=[scenes[0]])
    assert UNFRAMED in story_problems(lone, settings)


@pytest.mark.parametrize("case", NUMBERED)
def test_the_scene_count_follows_the_item_count(case: Numbered) -> None:
    settings = list_settings(GENERAL, case.structure, story={"item_count": 5})
    found = story_problems(case.story(), settings)
    assert "use exactly 7 scenes, not 9" in found
    assert "write exactly 5 numbered items, not 7" in found
    switched = settings.story.model_copy(update={"enabled_checks": [StoryCheck.WORDS_PER_SCENE]})
    assert story_problems(case.story(), settings.model_copy(update={"story": switched})) == []


@pytest.mark.parametrize("audience", AUDIENCES)
@pytest.mark.parametrize("case", NUMBERED)
def test_the_prompts_ask_for_numbered_items(case: Numbered, audience: TemplateAudience) -> None:
    settings = list_settings(audience, case.structure, story={"item_count": 5})
    request = story_request(settings, "a topic", "en")
    order = case.order(5).removeprefix("number the items ")
    assert "- Exactly 7 scenes.\n" in request.prompt
    assert f"exactly 5 item scenes, one item per scene, numbered {order}" in request.prompt
    assert case.format in (request.system or "")
    assert "$" not in request.prompt and "Cast (" not in request.prompt
    translation = translation_request(settings, case.story(), "en", "ta").prompt
    heading = case.story().scenes[1].heading
    assert '"scene_labels"' in translation and f'"heading": "{heading}"' in translation


@pytest.mark.parametrize("case", NUMBERED)
def test_a_numbered_script_supplies_its_count_items_and_defaults(case: Numbered) -> None:
    values = template_values(case.story(), list_settings(GENERAL, case.structure))
    assert values["count"] == "7" and values["items"].startswith(case.first_items)
    defaults = defaults_for(GENERAL, structure=case.structure)
    assert defaults["cast"] == [] and defaults["story"]["morals"] == []
    assert "{count}" in defaults["metadata"]["description_template"]["en"]
