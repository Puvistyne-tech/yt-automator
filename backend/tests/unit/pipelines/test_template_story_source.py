from __future__ import annotations

from pathlib import Path

import pytest

from autotube.pipelines.narrated_video.settings.story import StorySource
from autotube.pipelines.narrated_video.stages.story import GeneralScriptUnavailableError, StoryStage
from tests.fixtures.kids_data import StageRig, meta_of, quick_settings
from tests.fixtures.kids_fakes import FakeProviders, failing_writer
from tests.fixtures.template_settings import GENERAL, KIDS, model_for, quick_template_settings


@pytest.mark.parametrize("source", ["bundled_only", "llm_with_fallback"])
def test_a_general_model_pins_the_language_model_source(source: str) -> None:
    loaded = model_for(GENERAL).model_validate({"story": {"source": source}})
    assert loaded.story.source is StorySource.LLM_WITH_FALLBACK
    assert loaded.safety.audience is GENERAL


def test_a_kids_model_keeps_the_chosen_source() -> None:
    loaded = model_for(KIDS).model_validate({"story": {"source": "bundled_only"}})
    assert loaded.story.source is StorySource.BUNDLED_ONLY


@pytest.mark.parametrize("providers", [FakeProviders(writer=failing_writer()), FakeProviders()])
def test_a_general_story_never_falls_back_to_a_bundled_story(
    tmp_path: Path, providers: FakeProviders
) -> None:
    rig = StageRig(tmp_path, settings=quick_template_settings(), providers=providers)
    with pytest.raises(GeneralScriptUnavailableError, match="never falls back"):
        rig.run(StoryStage())
    assert meta_of(rig, "story") == []


def test_a_general_story_refuses_bundled_only_even_when_unpinned(tmp_path: Path) -> None:
    settings = quick_settings(story={"source": "bundled_only"}, safety={"audience": "general"})
    rig = StageRig(tmp_path, settings=settings)
    with pytest.raises(GeneralScriptUnavailableError):
        rig.run(StoryStage())


def test_a_kids_story_still_falls_back_to_a_bundled_story(tmp_path: Path) -> None:
    settings = quick_template_settings(KIDS)
    rig = StageRig(tmp_path, settings=settings, providers=FakeProviders(writer=failing_writer()))
    assert rig.run(StoryStage()).provider == "bundled"
