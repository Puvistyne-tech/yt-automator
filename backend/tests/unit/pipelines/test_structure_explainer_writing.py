from __future__ import annotations

from pathlib import Path

import pytest

from autotube.domain.pipeline_templates import TemplateAudience
from autotube.pipelines.narrated_video.stages.story import ScriptUnavailableError, StoryStage
from autotube.pipelines.narrated_video.story.child_terms import child_terms_in
from autotube.pipelines.narrated_video.story.prompts import story_request, translation_request
from tests.fixtures.explainer_data import (
    TAKEAWAY_ENDING,
    explainer_settings,
    explainer_story,
    explainer_writer,
)
from tests.fixtures.kids_data import StageRig, meta_of
from tests.fixtures.kids_fakes import FakeProviders, failing_writer
from tests.fixtures.quick_sections import QUICK_SECTIONS
from tests.fixtures.template_settings import GENERAL, KIDS

GENERAL_LINE = "The audience is general: the script must never address children"
FRAGMENT_LINE = "The first scene is the hook"


def test_a_kids_explainer_keeps_the_kids_system_lines() -> None:
    request = story_request(explainer_settings(KIDS), "how a rainbow forms", "en")
    system = request.system or ""
    assert "narrated explainer videos for children aged 3 to 7" in system
    assert "Reading level" in system and GENERAL_LINE not in system
    assert FRAGMENT_LINE in request.prompt and "Cast (" not in request.prompt


def test_a_general_explainer_prompt_never_addresses_children() -> None:
    settings = explainer_settings(GENERAL)
    request = story_request(settings, "how a rainbow forms", "en")
    system = request.system or ""
    assert GENERAL_LINE in system and "children aged" not in system
    assert child_terms_in(f"{system}\n{request.prompt}") == []
    assert "$" not in request.prompt and "$" not in system


@pytest.mark.parametrize("audience", [KIDS, GENERAL])
def test_an_explainer_translation_keeps_the_hook_and_takeaway(audience: TemplateAudience) -> None:
    settings = explainer_settings(audience, story=TAKEAWAY_ENDING)
    prompt = translation_request(settings, explainer_story(), "en", "ta").prompt
    assert "no recurring characters" in prompt
    assert "takeaway" in prompt and "question mark" in prompt
    assert "refrain" not in prompt


def stage_rig(root: Path, audience: TemplateAudience, providers: FakeProviders) -> StageRig:
    return StageRig(
        root, settings=explainer_settings(audience, **QUICK_SECTIONS), providers=providers
    )


@pytest.mark.parametrize(
    ("audience", "reason"),
    [(KIDS, "explainer scripts have no bundled fallback"), (GENERAL, "never falls back")],
)
def test_an_explainer_never_falls_back_to_a_bundled_story(
    tmp_path: Path, audience: TemplateAudience, reason: str
) -> None:
    rig = stage_rig(tmp_path, audience, FakeProviders(writer=failing_writer()))
    with pytest.raises(ScriptUnavailableError, match=reason):
        rig.run(StoryStage())
    assert meta_of(rig, "story") == []


@pytest.mark.parametrize("audience", [KIDS, GENERAL])
def test_an_explainer_is_written_by_the_language_model(
    tmp_path: Path, audience: TemplateAudience
) -> None:
    rig = stage_rig(tmp_path, audience, FakeProviders(writer=explainer_writer()))
    outcome = rig.run(StoryStage())
    assert outcome.provider != "bundled"
    assert {item.language for item in meta_of(rig, "story")} == {"en", "ta"}
