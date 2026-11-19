from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from autotube.domain.pipeline_templates import TemplateAudience
from autotube.domain.run_enums import ArtifactKind
from autotube.domain.run_parts import Artifact
from autotube.pipelines.narrated_video.publishing.metadata import upload_metadata
from autotube.pipelines.narrated_video.scoring.inputs import ScoreInputs
from autotube.pipelines.narrated_video.scoring.output_items import metadata_limits
from autotube.pipelines.narrated_video.settings.base import LocalizedText
from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.story.checks import story_problems, translation_problems
from autotube.pipelines.narrated_video.story.gates import (
    child_term_problems,
    reading_level_problems,
)
from autotube.pipelines.narrated_video.story.model import Story
from autotube.pipelines.narrated_video.story.prompts import story_request
from autotube.pipelines.narrated_video.template.definition import NarratedDefinition
from autotube.pipelines.narrated_video.template.settings_model import settings_model_for
from tests.fixtures.kids_data import draft_dict, story

GENERAL = settings_model_for(NarratedDefinition(), TemplateAudience.GENERAL)()
CLEAN = Story.model_validate({**draft_dict("leaf_boat"), "language": "en"})
KIDS = KidsStorySettings()
GENERAL_LINE = "The audience is general: the script must never address children"


def test_general_metadata_is_not_made_for_kids() -> None:
    assert upload_metadata(story(), GENERAL, "episode").made_for_kids is False
    assert upload_metadata(story(), KIDS, "episode").made_for_kids is True


def flagged(artifact: Artifact, made_for_kids: bool) -> Artifact:
    return artifact.model_copy(update={"meta": {**artifact.meta, "made_for_kids": made_for_kids}})


@pytest.mark.parametrize("kids", [True, False])
def test_the_made_for_kids_check_follows_the_audience(kids: bool) -> None:
    settings = KIDS if kids else GENERAL
    upload = Artifact(
        id="a-1",
        kind=ArtifactKind.METADATA,
        stage_id="package",
        filename="m.json",
        media_type="application/json",
        size_bytes=1,
        meta={"role": "upload_metadata", "title": "A title", "description": "", "tags": []},
    )
    inputs = ScoreInputs(settings, ("en",), (flagged(upload, kids),), Path(), {}, {}, None)
    good = metadata_limits(inputs)
    wrong = metadata_limits(replace(inputs, artifacts=(flagged(upload, not kids),)))
    assert good is not None and good.score == 100
    assert wrong is not None and wrong.score == 0
    assert good.detail.endswith("made for kids" if kids else "not made for kids")


def test_general_prompts_drop_the_children_lines_and_add_the_general_line() -> None:
    system = story_request(GENERAL, "sharing", "en").system or ""
    assert GENERAL_LINE in system
    assert "children aged" not in system and "Reading level" not in system
    assert GENERAL_LINE not in (story_request(KIDS, "sharing", "en").system or "")


@pytest.mark.parametrize(
    ("language", "hook", "found"),
    [("en", "Hey Kids, listen!", "kids"), ("ta", "வணக்கம், குழந்தைகளே!", "குழந்தைகளே")],
)
def test_the_term_gate_rejects_child_directed_scripts(language: str, hook: str, found: str) -> None:
    addressed = CLEAN.model_copy(update={"language": language, "hook_line": hook})
    expected = [f"the audience is general: never address children; remove: {found}"]
    assert child_term_problems(addressed, GENERAL) == expected
    assert child_term_problems(addressed, KIDS) == []


@pytest.mark.parametrize("hook", ["Kidney beans for dinner.", "குழந்தைகளேயில்லாத ஊர்."])
def test_the_term_gate_matches_whole_phrases_only(hook: str) -> None:
    assert child_term_problems(CLEAN.model_copy(update={"hook_line": hook}), GENERAL) == []
    assert child_term_problems(CLEAN, GENERAL) == []


def test_the_term_gate_screens_the_series_intro_and_outro_lines() -> None:
    series = GENERAL.series.model_copy(
        update={"intro_line": LocalizedText(en="Hello, little friends!", ta="வணக்கம்")}
    )
    framed = GENERAL.model_copy(update={"series": series})
    assert child_term_problems(CLEAN, framed) == [
        "the series intro or outro line must change in the settings: never address children; "
        "remove: little friends"
    ]


def gates_off() -> KidsStorySettings:
    story_rules = GENERAL.story.model_copy(update={"enabled_checks": []})
    return GENERAL.model_copy(update={"story": story_rules})


@pytest.mark.parametrize(
    ("language", "hook"), [("en", "Hey kids, listen!"), ("ta", "வணக்கம், குழந்தைகளே!")]
)
def test_the_term_gate_is_always_on_for_writing_and_translation(language: str, hook: str) -> None:
    addressed = CLEAN.model_copy(update={"language": language, "hook_line": hook})
    off = gates_off()
    assert any("never address children" in problem for problem in story_problems(addressed, off))
    assert any(
        "never address children" in problem for problem in translation_problems(addressed, off)
    )
    assert translation_problems(CLEAN.model_copy(update={"language": language}), off) == []


def test_general_scripts_skip_the_reading_level_check() -> None:
    wordy = story()
    strict = {"story": {"max_average_sentence_words": {"en": 1, "ta": 1}}}
    kids_strict = KidsStorySettings.model_validate(strict)
    general_strict = KidsStorySettings.model_validate({**strict, "safety": {"audience": "general"}})
    assert reading_level_problems(wordy, kids_strict)
    assert reading_level_problems(wordy, general_strict) == []
