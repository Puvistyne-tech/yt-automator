from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from autotube.domain.capabilities import TextRequest
from autotube.pipelines.narrated_video.stages.story import ScriptUnavailableError, StoryStage
from autotube.pipelines.narrated_video.story.checks import translation_problems
from autotube.pipelines.narrated_video.story.model import Story
from tests.fixtures.kids_data import StageRig, is_judge, is_translation
from tests.fixtures.kids_fakes import FakeProviders, FakeWriter, as_json
from tests.fixtures.list_data import list_settings, tamil_list, with_scene
from tests.fixtures.quick_sections import QUICK_SECTIONS
from tests.fixtures.quiz_data import quiz_draft, quiz_settings, quiz_text_ta, tamil_quiz
from tests.fixtures.template_settings import GENERAL, KIDS

QUESTION = "சூரியனுக்கு மிக அருகில் உள்ள கோள் எது"
CHOICES: dict[str, Any] = {"story": {"answer_choices": 3}}
ONE_LABEL = [{"heading": "ஒன்று"}]
TAMIL_CASES = [
    (False, 1, {"question": QUESTION}, "end question 1 with a question mark"),
    (False, 1, {"question": f"{QUESTION}？"}, None),
    (False, 2, {"answer": "வெள்ளி"}, "say the answer to question 1, word for word, in its reveal"),
    (False, 2, {"answer": ""}, "follow question 1 with a reveal scene that gives its answer"),
    (True, 1, {"choices": ["புதன்", "வெள்ளி"]}, "give question 1 exactly 3 choices"),
    (True, 1, {"choices": ["x", "y", "z"]}, "make the answer to question 1 one of its choices"),
]


@pytest.mark.parametrize(("choices", "index", "changes", "problem"), TAMIL_CASES)
def test_tamil_quiz_translations_run_every_quiz_gate(
    choices: bool, index: int, changes: dict[str, Any], problem: str | None
) -> None:
    settings = quiz_settings(GENERAL, **(CHOICES if choices else {}))
    tamil = with_scene(tamil_quiz(choices), index, **changes)
    assert translation_problems(tamil, settings) == ([problem] if problem else [])


def test_tamil_list_translations_keep_distinct_headings() -> None:
    tamil = with_scene(tamil_list(), 2, heading="தேனீக்கள் நடனமாடிப் பேசும்")
    assert translation_problems(tamil, list_settings(KIDS)) == ["give every item its own heading"]


def test_tamil_labels_are_screened_for_a_general_audience() -> None:
    tamil = with_scene(tamil_quiz(), 1, question=f"குழந்தைகளே, {QUESTION}?")
    found = translation_problems(tamil, quiz_settings(GENERAL))
    assert any("never address children" in item for item in found)
    assert translation_problems(tamil, quiz_settings(KIDS)) == []


@pytest.mark.parametrize("translated", [tamil_list, tamil_quiz], ids=["list", "quiz"])
@pytest.mark.parametrize("labels", [None, ONE_LABEL], ids=["missing", "short"])
def test_a_translation_must_keep_one_label_entry_per_scene(
    translated: Callable[..., Story], labels: list[dict[str, str]] | None
) -> None:
    with pytest.raises(ValueError, match="one scene_labels entry per scene"):
        translated(scene_labels=labels)


def unlabelled_writer(labels: list[dict[str, str]] | None) -> FakeWriter:
    def respond(request: TextRequest) -> str:
        if is_judge(request):
            return "1"
        if is_translation(request):
            return as_json({**quiz_text_ta(), "scene_labels": labels})
        return as_json(quiz_draft())

    return FakeWriter(respond)


@pytest.mark.parametrize("labels", [None, ONE_LABEL], ids=["missing", "short"])
def test_a_translation_without_every_label_is_retried_then_fails(
    tmp_path: Path, labels: list[dict[str, str]] | None
) -> None:
    settings = quiz_settings(GENERAL, **QUICK_SECTIONS)
    writer = unlabelled_writer(labels)
    rig = StageRig(tmp_path, settings=settings, providers=FakeProviders(writer=writer))
    with pytest.raises(ScriptUnavailableError):
        rig.run(StoryStage())
    translations = [request for request in writer.requests if is_translation(request)]
    assert len(translations) == settings.story.max_attempts
    assert '"scene_labels"' in translations[0].prompt


def test_translated_choices_replace_the_source_choices() -> None:
    assert tamil_quiz(choices=True).scenes[1].choices == ["புதன்", "வெள்ளி", "செவ்வாய்"]
