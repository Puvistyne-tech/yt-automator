from __future__ import annotations

import json
from pathlib import Path

import pytest

from autotube.domain.pipeline_templates import TemplateAudience
from autotube.pipelines.narrated_video.stages.story import ScriptUnavailableError, StoryStage
from autotube.pipelines.narrated_video.story.child_terms import child_terms_in
from autotube.pipelines.narrated_video.story.prompts import story_request, translation_request
from tests.fixtures.explainer_data import (
    HOOKLESS,
    TAKEAWAY_ENDING,
    explainer_draft,
    explainer_settings,
    explainer_story,
    explainer_writer,
)
from tests.fixtures.kids_data import StageRig, meta_of
from tests.fixtures.kids_fakes import FakeProviders, as_json, failing_writer, scripted_writer
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
    with pytest.raises(ScriptUnavailableError, match=reason) as raised:
        rig.run(StoryStage())
    assert "story writer unavailable" in str(raised.value)
    assert meta_of(rig, "story") == []


def test_a_rejected_general_explainer_names_the_last_failed_checks(tmp_path: Path) -> None:
    draft = explainer_draft()
    draft["scenes"][0] = {**draft["scenes"][0], "narration": HOOKLESS}
    rig = stage_rig(tmp_path, GENERAL, FakeProviders(writer=scripted_writer([as_json(draft)] * 3)))
    with pytest.raises(ScriptUnavailableError, match="never falls back") as raised:
        rig.run(StoryStage())
    message = str(raised.value)
    assert "; the last story attempt 3 failed checks (" in message
    assert "8 scenes, about " in message and "): open the first scene with the question" in message
    record = json.loads((tmp_path / "story" / "attempt-3-en.json").read_text(encoding="utf-8"))
    assert record["failed_checks"][0].startswith("open the first scene")
    assert record["script"]["scenes"][0]["narration"] == HOOKLESS


@pytest.mark.parametrize("audience", [KIDS, GENERAL])
def test_an_explainer_is_written_by_the_language_model(
    tmp_path: Path, audience: TemplateAudience
) -> None:
    rig = stage_rig(tmp_path, audience, FakeProviders(writer=explainer_writer()))
    outcome = rig.run(StoryStage())
    assert outcome.provider != "bundled"
    assert {item.language for item in meta_of(rig, "story")} == {"en", "ta"}
