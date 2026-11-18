from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from autotube.domain.quality import ScoreItem
from autotube.domain.srt import SrtEntry
from autotube.pipelines.kids_story.plugin import KidsStoryPipeline
from autotube.pipelines.kids_story.scoring.content_items import (
    character_consistency,
    reading_level,
)
from autotube.pipelines.kids_story.scoring.inputs import ScoreInputs, gathered
from autotube.pipelines.kids_story.scoring.measures import (
    SubtitleRules,
    range_score,
    subtitle_track,
)
from autotube.pipelines.kids_story.scoring.output_items import (
    completeness,
    loudness,
    metadata_limits,
)
from autotube.pipelines.kids_story.scoring.timing_items import (
    episode_duration,
    short_duration,
    speaking_rate,
    subtitle_timing,
)
from tests.fixtures.kids_data import StageRig, quick_settings, run_chain
from tests.fixtures.kids_fakes import FakeMedia, FakeProviders, FakeSpeech

RULES = SubtitleRules(min_coverage=0.95, overlap_penalty=0.5, out_of_bounds_penalty=0.5)


def finished(
    root: Path, providers: FakeProviders | None = None, languages: tuple[str, ...] = ("en", "ta")
) -> StageRig:
    return run_chain(StageRig(root, providers=providers or FakeProviders(), languages=languages))


@pytest.fixture(scope="module")
def inputs(tmp_path_factory: pytest.TempPathFactory) -> ScoreInputs:
    return gathered(finished(tmp_path_factory.mktemp("score")).context())


def required(item: ScoreItem | None) -> ScoreItem:
    assert item is not None
    return item


def test_range_score_and_subtitle_track_measures() -> None:
    assert range_score(5, 0, 10, 2) == 100 and range_score(13, 0, 10, 10) == 70
    good = [
        SrtEntry(start=0, end=1, lines=("one two",)),
        SrtEntry(start=1, end=2, lines=("three",)),
    ]
    assert subtitle_track(good, 2.0, 3, RULES).score == 100
    overlapping = [
        SrtEntry(start=0, end=1.5, lines=("one two",)),
        SrtEntry(start=1, end=2, lines=("three",)),
    ]
    assert subtitle_track(overlapping, 2.0, 3, RULES).score == 50
    outside = [SrtEntry(start=0, end=5, lines=("one two three",))]
    assert subtitle_track(outside, 2.0, 3, RULES).score == 50
    strict = RULES.model_copy(update={"min_coverage": 1.0})
    assert subtitle_track(good, 2.0, 6, strict).score == 50
    gentle = RULES.model_copy(update={"overlap_penalty": 0.9, "out_of_bounds_penalty": 1.0})
    assert subtitle_track(overlapping, 2.0, 3, gentle).score == 90
    assert subtitle_track(outside, 2.0, 3, gentle).score == 100
    assert subtitle_track([], 2.0, 0, RULES).score == 100
    assert subtitle_track([], 2.0, 5, RULES).score == 0


def test_a_clean_run_scores_well_on_every_item(inputs: ScoreInputs) -> None:
    items = {
        item.id: item
        for item in KidsStoryPipeline().score(
            StageRig(inputs.workspace, artifacts=list(inputs.artifacts)).context()
        )
    }
    assert set(items) == {
        "subtitle_timing",
        "episode_duration",
        "short_duration",
        "speaking_rate",
        "reading_level",
        "moral_and_refrain",
        "character_consistency",
        "metadata_limits",
        "loudness",
        "completeness",
    }
    for item_id in (
        "subtitle_timing",
        "episode_duration",
        "speaking_rate",
        "short_duration",
        "moral_and_refrain",
        "character_consistency",
        "metadata_limits",
        "loudness",
        "completeness",
        "reading_level",
    ):
        assert items[item_id].score == 100, items[item_id].detail
    assert items["subtitle_timing"].weight == 2.0


def test_durations_and_speaking_rate_follow_settings(inputs: ScoreInputs) -> None:
    tight = quick_settings(story={"target_duration_seconds": 30, "duration_tolerance_seconds": 0})
    narration = {
        code: sum(line.seconds for key, line in lines.items() if key.startswith("scene-"))
        for code, lines in inputs.voices.items()
    }
    expected = sum(max(100 - 2 * (seconds - 30), 0) for seconds in narration.values()) / 2
    item = required(episode_duration(replace(inputs, settings=tight)))
    assert item.score == pytest.approx(expected) and "of narration" in item.detail
    short_limit = quick_settings(short={"max_duration_seconds": 10})
    assert required(short_duration(replace(inputs, settings=short_limit))).score < 100
    assert (
        short_duration(replace(inputs, settings=quick_settings(short={"enabled": False}))) is None
    )
    slow = quick_settings(
        quality={
            "words_per_minute_min": {"en": 500, "ta": 500},
            "words_per_minute_max": {"en": 600, "ta": 600},
        }
    )
    assert required(speaking_rate(replace(inputs, settings=slow))).score == 0


def test_content_items_react_to_changed_rules(inputs: ScoreInputs) -> None:
    strict = quick_settings(story={"max_average_sentence_words": {"en": 2, "ta": 2}})
    assert required(reading_level(replace(inputs, settings=strict))).score == 50
    recast = [
        member.model_copy(update={"visual_descriptor": "a purple dragon"})
        for member in inputs.settings.cast
    ]
    changed = inputs.settings.model_copy(update={"cast": recast})
    assert required(character_consistency(replace(inputs, settings=changed))).score == 0


def test_output_items_find_problems(inputs: ScoreInputs) -> None:
    broken = [
        item.model_copy(update={"meta": {**item.meta, "title": "x" * 101}})
        if item.meta.get("role") == "upload_metadata" and item.language == "en"
        else item
        for item in inputs.artifacts
    ]
    assert required(metadata_limits(replace(inputs, artifacts=tuple(broken)))).score == 50
    loud = replace(inputs, media=FakeMedia(loudness=-30.0))
    assert required(loudness(loud)).score < 100
    assert loudness(replace(inputs, media=None)) is None
    without_thumbnails = tuple(
        item for item in inputs.artifacts if item.meta.get("role") != "thumbnail"
    )
    item = completeness(replace(inputs, artifacts=without_thumbnails))
    assert item.score == 75 and "thumbnail en episode" in item.detail


def test_missing_word_timings_lower_subtitle_coverage(tmp_path: Path) -> None:
    rig = finished(
        tmp_path, providers=FakeProviders(speech=FakeSpeech(with_words=False)), languages=("en",)
    )
    inputs = gathered(rig.context())
    item = required(subtitle_timing(inputs))
    assert item.score == 0 and "coverage 0%" in item.detail
    assert completeness(inputs).score < 100


def test_scoring_without_artifacts_reports_only_completeness(tmp_path: Path) -> None:
    items = KidsStoryPipeline().score(StageRig(tmp_path).context())
    assert [item.id for item in items] == ["completeness"] and items[0].score == 0
