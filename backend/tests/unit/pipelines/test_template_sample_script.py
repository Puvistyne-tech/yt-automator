from __future__ import annotations

from typing import Any

import pytest

from autotube.domain.capabilities import Capability, TextRequest
from autotube.domain.pipeline_templates import TemplateAudience
from autotube.domain.provider_fallbacks import ProviderFallback
from autotube.domain.sample_scripts import SampleScene, SampleScript, SampleUnavailableError
from autotube.pipelines.narrated_video.engine import NarratedVideoEngine
from autotube.pipelines.narrated_video.settings.base import LocalizedText
from autotube.pipelines.narrated_video.story.model import StoryScene
from autotube.pipelines.narrated_video.story.themes import choose_theme
from autotube.pipelines.narrated_video.template.sample import (
    REJECTED,
    UNAVAILABLE,
    sample_scene,
    settings_sample,
)
from autotube.shared.errors import RuleConflict
from tests.fixtures.explainer_data import explainer_draft, explainer_writer
from tests.fixtures.kids_data import (
    draft_dict,
    is_judge,
    is_translation,
    smart_writer,
    tamil_text,
)
from tests.fixtures.kids_fakes import FakeProviders, FakeWriter, as_json, failing_writer
from tests.fixtures.list_data import list_draft, list_writer
from tests.fixtures.quiz_data import quiz_draft, quiz_writer
from tests.fixtures.template_records import template
from tests.fixtures.template_settings import (
    GENERAL,
    KIDS,
    general_draft,
    general_writer,
    model_for,
)

EXPLAINER = {"structure": "explainer"}


def sample(
    audience: TemplateAudience,
    writer: FakeWriter | None,
    topic: str = "",
    language: str = "en",
    **definition: Any,
) -> SampleScript:
    made = template(audience=audience, definition=definition)
    return NarratedVideoEngine().sample_script(made, language, topic, FakeProviders(writer=writer))


def writing_requests(writer: FakeWriter) -> list[TextRequest]:
    return [r for r in writer.requests if not is_judge(r) and not is_translation(r)]


@pytest.mark.parametrize(
    ("audience", "writer", "definition", "draft"),
    [
        (KIDS, smart_writer(), {}, draft_dict()),
        (GENERAL, general_writer(), {}, general_draft()),
        (GENERAL, explainer_writer(), EXPLAINER, explainer_draft()),
        (GENERAL, list_writer(), {"structure": "list"}, list_draft()),
        (KIDS, list_writer(countdown=True), {"structure": "countdown"}, list_draft(True)),
        (KIDS, quiz_writer(), {"structure": "quiz"}, quiz_draft()),
    ],
    ids=["kids-story", "general-story", "explainer", "list", "countdown", "quiz"],
)
def test_a_sample_comes_from_the_writer(
    audience: TemplateAudience,
    writer: FakeWriter,
    definition: dict[str, Any],
    draft: dict[str, Any],
) -> None:
    script = sample(audience, writer, **definition)
    assert (script.language, script.title, script.provider) == ("en", draft["title"], "fake-llm")
    assert script.takeaway == draft.get("moral", "")
    assert [scene.narration for scene in script.scenes] == [s["narration"] for s in draft["scenes"]]
    assert [scene.heading for scene in script.scenes] == [
        s.get("heading", "") for s in draft["scenes"]
    ]
    assert script.upload_title and script.upload_description


def test_the_topic_reaches_the_writer() -> None:
    writer = smart_writer()
    sample(KIDS, writer, "sharing")
    assert "sharing" in writer.requests[0].prompt


@pytest.mark.parametrize("topic", ["", "   "])
def test_an_empty_topic_uses_the_seeded_theme(topic: str) -> None:
    writer = smart_writer()
    sample(KIDS, writer, topic)
    seeded = choose_theme(model_for(KIDS)().story, template().id)
    assert seeded and seeded in writer.requests[0].prompt


def test_a_second_language_sample_is_written_first_and_translated() -> None:
    writer = smart_writer()
    script = sample(KIDS, writer, language="ta")
    assert (script.language, script.title) == ("ta", tamil_text()["title"])
    assert [is_translation(r) for r in writer.requests if not is_judge(r)] == [False, True]


def test_a_second_language_sample_runs_the_translation_gates() -> None:
    def respond(request: TextRequest) -> str:
        if is_translation(request):
            return as_json(tamil_text() | {"narrations": ["ஒன்று."]})
        return "2" if is_judge(request) else as_json(draft_dict())

    with pytest.raises(SampleUnavailableError) as refused:
        sample(KIDS, FakeWriter(respond), language="ta")
    assert str(refused.value) == REJECTED


@pytest.mark.parametrize(("overlay", "attempts"), [({}, 1), ({"preview_attempts": 2}, 2)])
def test_a_sample_tries_the_preview_attempts(overlay: dict[str, Any], attempts: int) -> None:
    short = draft_dict() | {"scenes": draft_dict()["scenes"][:1]}
    writer = FakeWriter(lambda _: as_json(short))
    with pytest.raises(SampleUnavailableError) as refused:
        sample(KIDS, writer, settings={"story": overlay})
    assert str(refused.value) == REJECTED
    assert len(writing_requests(writer)) == attempts


@pytest.mark.parametrize("audience", [KIDS, GENERAL])
@pytest.mark.parametrize("writer", [None, failing_writer()])
def test_a_missing_or_failing_writer_never_falls_back_to_a_bundled_story(
    audience: TemplateAudience, writer: FakeWriter | None
) -> None:
    with pytest.raises(SampleUnavailableError) as refused:
        sample(audience, writer)
    assert str(refused.value) == UNAVAILABLE


class RefusingProviders:
    def fallbacks(self) -> tuple[ProviderFallback, ...]:
        return ()

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
    with pytest.raises(SampleUnavailableError) as refused:
        sample(GENERAL, child_directed_writer(), **EXPLAINER)
    assert str(refused.value) == REJECTED


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
