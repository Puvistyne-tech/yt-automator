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
from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.story.gates import (
    child_term_problems,
    reading_level_problems,
    story_problems,
    translation_problems,
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


def test_the_term_gate_rejects_child_directed_scripts_in_english_and_tamil() -> None:
    english = CLEAN.model_copy(update={"hook_line": "Hey kids, listen!"})
    tamil = CLEAN.model_copy(update={"language": "ta", "hook_line": "வணக்கம், குழந்தைகளே!"})
    assert child_term_problems(english, GENERAL) == [
        "the audience is general: never address children; remove: kids"
    ]
    assert child_term_problems(tamil, GENERAL) == [
        "the audience is general: never address children; remove: குழந்தைகளே"
    ]
    assert child_term_problems(english, KIDS) == []
    assert child_term_problems(CLEAN, GENERAL) == []


def test_the_term_gate_is_always_on_for_writing_and_translation() -> None:
    english = story().model_copy(update={"hook_line": "Hey kids, listen!"})
    off = GENERAL.model_copy(
        update={"story": GENERAL.story.model_copy(update={"enabled_checks": []})}
    )
    assert any("never address children" in problem for problem in story_problems(english, off))
    assert any(
        "never address children" in problem for problem in translation_problems(english, off)
    )


def test_general_scripts_skip_the_reading_level_check() -> None:
    wordy = story()
    strict = {"story": {"max_average_sentence_words": {"en": 1, "ta": 1}}}
    kids_strict = KidsStorySettings.model_validate(strict)
    general_strict = KidsStorySettings.model_validate({**strict, "safety": {"audience": "general"}})
    assert reading_level_problems(wordy, kids_strict)
    assert reading_level_problems(wordy, general_strict) == []
