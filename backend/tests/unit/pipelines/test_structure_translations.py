from __future__ import annotations

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

TAMIL_ANSWER = "say the answer to question 1, word for word, in its reveal"


@pytest.mark.parametrize(
    ("index", "changes", "problem"),
    [
        (
            1,
            {"question": "சூரியனுக்கு மிக அருகில் உள்ள கோள் எது"},
            "end question 1 with a question mark",
        ),
        (2, {"answer": "வெள்ளி"}, TAMIL_ANSWER),
        (1, {"question": "சூரியனுக்கு மிக அருகில் உள்ள கோள் எது？"}, None),
    ],
)
def test_tamil_quiz_translations_keep_question_marks_and_answers(
    index: int, changes: dict[str, Any], problem: str | None
) -> None:
    tamil = with_scene(tamil_quiz(), index, **changes)
    assert translation_problems(tamil, quiz_settings(GENERAL)) == ([problem] if problem else [])


def test_tamil_list_translations_keep_distinct_headings() -> None:
    tamil = with_scene(tamil_list(), 2, heading="தேனீக்கள் நடனமாடிப் பேசும்")
    assert translation_problems(tamil, list_settings(KIDS)) == ["give every item its own heading"]


def test_tamil_labels_are_screened_for_a_general_audience() -> None:
    tamil = with_scene(tamil_quiz(), 1, question="குழந்தைகளே, சூரியனுக்கு அருகில் உள்ள கோள் எது?")
    found = translation_problems(tamil, quiz_settings(GENERAL))
    assert any("never address children" in item for item in found)
    assert translation_problems(tamil, quiz_settings(KIDS)) == []


def labelless_writer() -> FakeWriter:
    def respond(request: TextRequest) -> str:
        if is_judge(request):
            return "1"
        if is_translation(request):
            return as_json({**quiz_text_ta(), "scene_labels": None})
        return as_json(quiz_draft())

    return FakeWriter(respond)


def test_a_translation_without_scene_labels_is_retried_then_fails(tmp_path: Path) -> None:
    settings = quiz_settings(GENERAL, **QUICK_SECTIONS)
    writer = labelless_writer()
    rig = StageRig(tmp_path, settings=settings, providers=FakeProviders(writer=writer))
    with pytest.raises(ScriptUnavailableError):
        rig.run(StoryStage())
    translations = [request for request in writer.requests if is_translation(request)]
    assert len(translations) == settings.story.max_attempts
    assert '"scene_labels"' in translations[0].prompt


def test_translated_answers_replace_the_source_answers() -> None:
    tamil: Story = tamil_quiz(choices=True)
    assert tamil.scenes[1].choices == ["புதன்", "வெள்ளி", "செவ்வாய்"]
    assert [scene.number for scene in tamil.scenes] == [None] * len(tamil.scenes)
