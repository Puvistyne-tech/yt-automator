from __future__ import annotations

import pytest

from autotube.domain.pipeline_templates import PipelineTemplate
from autotube.pipelines.narrated_video.engine import NarratedVideoEngine
from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.settings.story_choices import EndingStyle
from autotube.pipelines.narrated_video.story.checks import story_problems
from autotube.pipelines.narrated_video.story.prompts import story_request, translation_request
from autotube.pipelines.narrated_video.structures.registry import spec_of
from tests.fixtures.builtin_catalog import BUILTIN_IDS
from tests.fixtures.explainer_data import explainer_story

ENGINE = NarratedVideoEngine()
BUILTINS = {item.id: item for item in ENGINE.builtin_templates()}
HISTORY = "history_in_five_minutes"
MORAL_FIELD = 'in "moral"'
MORAL_PLACEHOLDERS = ("{takeaway}", "{moral}")


def settings_of(item: PipelineTemplate) -> KidsStorySettings:
    settings = ENGINE.pipeline(item).settings_model()
    assert isinstance(settings, KidsStorySettings)
    return settings


def asks_for_moral(settings: KidsStorySettings) -> bool:
    problems = story_problems(explainer_story(moral=""), settings)
    return any(MORAL_FIELD in problem for problem in problems)


def descriptions_of(settings: KidsStorySettings) -> str:
    return " ".join(settings.metadata.description_template.model_dump().values())


def with_ending(settings: KidsStorySettings, style: EndingStyle) -> KidsStorySettings:
    story = settings.story.model_copy(update={"ending_style": style})
    return settings.model_copy(update={"story": story})


def test_every_builtin_is_listed() -> None:
    assert sorted(BUILTINS) == sorted(BUILTIN_IDS)


@pytest.mark.parametrize("template_id", BUILTIN_IDS)
def test_a_builtin_asks_for_a_moral_only_when_its_format_and_ending_have_one(
    template_id: str,
) -> None:
    settings = settings_of(BUILTINS[template_id])
    required = spec_of(settings).moral_required(settings)
    assert asks_for_moral(settings) is required
    if any(slot in descriptions_of(settings) for slot in MORAL_PLACEHOLDERS):
        assert required


def test_an_open_ended_explainer_is_not_asked_for_a_takeaway() -> None:
    settings = with_ending(settings_of(BUILTINS[HISTORY]), EndingStyle.OPEN)
    script = explainer_story(moral="")
    problems = " ".join(story_problems(script, settings))
    assert "takeaway" not in problems and "moral" not in problems
    assert '"moral" is an empty string.' in story_request(settings, "maps", "en").prompt
    assert "takeaway" not in translation_request(settings, script, "en", "ta").prompt


def test_the_history_template_keeps_its_takeaway_and_names_it() -> None:
    settings = settings_of(BUILTINS[HISTORY])
    problems = story_problems(explainer_story(moral=""), settings)
    assert 'write the takeaway in "moral"' in problems
    assert "says the takeaway word for word" in story_request(settings, "maps", "en").prompt
