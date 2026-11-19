from __future__ import annotations

from typing import Any

import pytest

from autotube.domain.capabilities import Capability
from autotube.domain.pipeline_templates import TemplateAudience
from autotube.domain.sample_scripts import SampleScene, SampleScript, SampleUnavailableError
from autotube.pipelines.narrated_video.engine import NarratedVideoEngine
from autotube.pipelines.narrated_video.settings.base import LocalizedText
from autotube.pipelines.narrated_video.story.model import StoryScene
from autotube.pipelines.narrated_video.template.sample import (
    REJECTED,
    UNAVAILABLE,
    sample_scene,
    settings_sample,
)
from autotube.shared.errors import RuleConflict
from tests.fixtures.explainer_data import TAKEAWAY_EN, explainer_draft, explainer_writer
from tests.fixtures.kids_data import draft_dict, is_judge, smart_writer
from tests.fixtures.kids_fakes import FakeProviders, FakeWriter, as_json, failing_writer
from tests.fixtures.template_records import template
from tests.fixtures.template_settings import GENERAL, KIDS, general_writer, model_for

EXPLAINER = {"structure": "explainer"}


def sample(
    audience: TemplateAudience,
    writer: FakeWriter | None,
    topic: str = "",
    **definition: Any,
) -> SampleScript:
    made = template(audience=audience, definition=definition)
    return NarratedVideoEngine().sample_script(made, "en", topic, FakeProviders(writer=writer))


def test_a_kids_story_sample_comes_from_the_writer() -> None:
    writer = smart_writer()
    script = sample(KIDS, writer, "sharing")
    draft = draft_dict()
    assert (script.language, script.title, script.provider) == ("en", draft["title"], "fake-llm")
    assert script.takeaway == draft["moral"]
    assert [scene.narration for scene in script.scenes] == [s["narration"] for s in draft["scenes"]]
    assert script.upload_title and script.upload_description
    assert "sharing" in writer.requests[0].prompt


def test_a_general_explainer_sample_comes_from_the_writer() -> None:
    script = sample(GENERAL, explainer_writer(), **EXPLAINER)
    assert (script.title, script.takeaway) == (explainer_draft()["title"], TAKEAWAY_EN)
    assert len(script.scenes) == len(explainer_draft()["scenes"])
    assert script.provider == "fake-llm"


def test_a_general_story_sample_comes_from_the_writer() -> None:
    assert sample(GENERAL, general_writer()).provider == "fake-llm"


@pytest.mark.parametrize("audience", [KIDS, GENERAL])
@pytest.mark.parametrize("writer", [None, failing_writer()])
def test_a_missing_or_failing_writer_never_falls_back_to_a_bundled_story(
    audience: TemplateAudience, writer: FakeWriter | None
) -> None:
    with pytest.raises(SampleUnavailableError) as refused:
        sample(audience, writer)
    assert str(refused.value) == UNAVAILABLE


class RefusingProviders:
    def resolve(self, capability: Capability) -> Any:
        raise RuleConflict("provider_unavailable", f"no {capability.value} provider is ready")


def test_an_unavailable_provider_chain_is_an_unavailable_writer() -> None:
    made = template(audience=GENERAL)
    with pytest.raises(SampleUnavailableError, match="not available"):
        NarratedVideoEngine().sample_script(made, "en", "", RefusingProviders())


def child_directed_writer() -> FakeWriter:
    draft = explainer_draft() | {"hook_line": "Hey kids, listen!"}
    return FakeWriter(lambda request: "1" if is_judge(request) else as_json(draft))


def test_a_general_sample_runs_the_child_term_gate() -> None:
    writer = child_directed_writer()
    with pytest.raises(SampleUnavailableError) as refused:
        sample(GENERAL, writer, **EXPLAINER)
    assert str(refused.value) == REJECTED
    assert len(writer.requests) >= 2


def test_a_kids_sample_runs_the_script_gates() -> None:
    short = draft_dict() | {"scenes": draft_dict()["scenes"][:1]}
    with pytest.raises(SampleUnavailableError, match="passed the checks"):
        sample(KIDS, FakeWriter(lambda _: as_json(short)))


class HeadedScene(StoryScene):
    heading: str = ""


def test_a_sample_scene_keeps_the_heading_and_action_where_present() -> None:
    plain = StoryScene(narration="Hello.", visual="a hill")
    headed = HeadedScene(narration="One.", visual="a hill", heading="First", action="waves")
    assert sample_scene(plain) == SampleScene(narration="Hello.")
    assert sample_scene(headed) == SampleScene(narration="One.", heading="First", action="waves")


def test_general_upload_details_are_screened_like_the_package_stage() -> None:
    settings = model_for(GENERAL)()
    addressed = LocalizedText(en="A video for kids.", ta="")
    metadata = settings.metadata.model_copy(update={"description_template": addressed})
    screened = settings.model_copy(update={"metadata": metadata})
    providers = FakeProviders(writer=general_writer())
    with pytest.raises(SampleUnavailableError, match="never address children"):
        settings_sample(screened, "en", "", providers, "seed")
