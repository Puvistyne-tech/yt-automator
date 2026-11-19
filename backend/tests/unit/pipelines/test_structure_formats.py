from __future__ import annotations

from pathlib import Path

import pytest

from autotube.domain.pipeline_templates import TemplateAudience
from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.stages.story import ScriptUnavailableError, StoryStage
from autotube.pipelines.narrated_video.story.child_terms import child_terms_in
from autotube.pipelines.narrated_video.story.prompts import story_request
from tests.fixtures.kids_data import StageRig, meta_of
from tests.fixtures.kids_fakes import FakeProviders, failing_writer
from tests.fixtures.quick_sections import QUICK_SECTIONS
from tests.fixtures.structure_writers import SCRIPTED_WRITERS
from tests.fixtures.template_settings import GENERAL, KIDS, model_for

STRUCTURES = list(SCRIPTED_WRITERS)
GENERAL_LINE = "The audience is general: the script must never address children"


def settings_of(audience: TemplateAudience, structure: str) -> KidsStorySettings:
    return model_for(audience, structure=structure).model_validate(QUICK_SECTIONS)


@pytest.mark.parametrize("structure", STRUCTURES)
def test_a_kids_script_keeps_the_kids_system_lines(structure: str) -> None:
    system = story_request(settings_of(KIDS, structure), "a topic", "en").system or ""
    assert "videos for children aged 3 to 7" in system and GENERAL_LINE not in system


@pytest.mark.parametrize("structure", STRUCTURES)
def test_a_general_script_prompt_never_addresses_children(structure: str) -> None:
    request = story_request(settings_of(GENERAL, structure), "a topic", "en")
    system = request.system or ""
    assert GENERAL_LINE in system and "children aged" not in system
    assert child_terms_in(f"{system}\n{request.prompt}") == []
    assert "$" not in request.prompt + system


@pytest.mark.parametrize("structure", STRUCTURES)
@pytest.mark.parametrize(
    ("audience", "reason"),
    [(KIDS, "scripts have no bundled fallback"), (GENERAL, "never falls back")],
)
def test_a_failing_writer_fails_the_story_stage(
    tmp_path: Path, structure: str, audience: TemplateAudience, reason: str
) -> None:
    providers = FakeProviders(writer=failing_writer())
    rig = StageRig(tmp_path, settings=settings_of(audience, structure), providers=providers)
    with pytest.raises(ScriptUnavailableError, match=reason):
        rig.run(StoryStage())
    assert meta_of(rig, "story") == []


@pytest.mark.parametrize("structure", STRUCTURES)
@pytest.mark.parametrize("audience", [KIDS, GENERAL])
def test_a_script_is_written_and_translated_by_the_language_model(
    tmp_path: Path, structure: str, audience: TemplateAudience
) -> None:
    providers = FakeProviders(writer=SCRIPTED_WRITERS[structure]())
    rig = StageRig(tmp_path, settings=settings_of(audience, structure), providers=providers)
    assert rig.run(StoryStage()).provider != "bundled"
    assert {item.language for item in meta_of(rig, "story")} == {"en", "ta"}
