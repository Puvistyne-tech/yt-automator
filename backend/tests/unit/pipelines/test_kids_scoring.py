from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from automator.domain.quality import ScoreItem
from automator.pipelines.kids_story.plugin import KidsStoryPipeline
from automator.pipelines.kids_story.scoring.content_items import (
    character_consistency,
    moral_and_refrain,
    reading_level,
)
from automator.pipelines.kids_story.scoring.inputs import ScoreInputs, gathered
from automator.pipelines.kids_story.scoring.measures import range_score, subtitle_track
from automator.pipelines.kids_story.scoring.output_items import (
    completeness,
    loudness,
    metadata_limits,
)
from automator.pipelines.kids_story.scoring.timing_items import (
    episode_duration,
    short_duration,
    speaking_rate,
    subtitle_timing,
)
from automator.pipelines.kids_story.subtitles.srt import SrtEntry
from tests.unit.pipelines.kids_data import StageRig, quick_settings
from tests.unit.pipelines.kids_fakes import FakeMedia, FakeProviders, FakeSpeech


def finished(
    root: Path, providers: FakeProviders | None = None, languages: tuple[str, ...] = ("en", "ta")
) -> StageRig:
    rig = StageRig(root, providers=providers or FakeProviders(), languages=languages)
    for stage in KidsStoryPipeline().stages():
        rig.run(stage)
    return rig


@pytest.fixture(scope="module")
def inputs(tmp_path_factory: pytest.TempPathFactory) -> ScoreInputs:
    return gathered(finished(tmp_path_factory.mktemp("score")).context())


def required(item: ScoreItem | None) -> ScoreItem:
    assert item is not None
    return item


def test_range_score_and_subtitle_track_measures() -> None:
    assert range_score(5, 0, 10, 2) == 100 and range_score(13, 0, 10, 10) == 70
    good = [SrtEntry(start=0, end=1, text="one two"), SrtEntry(start=1, end=2, text="three")]
    assert subtitle_track(good, 2.0, 3, 0.95).score == 100
    overlapping = [
        SrtEntry(start=0, end=1.5, text="one two"),
        SrtEntry(start=1, end=2, text="three"),
    ]
    assert subtitle_track(overlapping, 2.0, 3, 0.95).score == 50
    outside = [SrtEntry(start=0, end=5, text="one two three")]
    assert subtitle_track(outside, 2.0, 3, 0.95).score == 50
    assert subtitle_track(good, 2.0, 6, 1.0).score == 50


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
    assert required(episode_duration(replace(inputs, settings=tight))).score < 5
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
    refrain = quick_settings(series={"refrain": {"en": "Hip hip hooray!", "ta": "ஆஹா!"}})
    assert required(moral_and_refrain(replace(inputs, settings=refrain))).score == 50
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
    item = required(subtitle_timing(gathered(rig.context())))
    assert item.score == 100 and "coverage 100%" in item.detail
    assert (tmp_path / "subtitles" / "en-episode.srt").read_text() == ""


def test_scoring_without_artifacts_reports_only_completeness(tmp_path: Path) -> None:
    items = KidsStoryPipeline().score(StageRig(tmp_path).context())
    assert [item.id for item in items] == ["completeness"] and items[0].score == 0
