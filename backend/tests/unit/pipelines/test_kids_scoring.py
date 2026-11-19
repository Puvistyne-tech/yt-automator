from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

import pytest

from autotube.domain.capabilities import Capability
from autotube.domain.provider_fallbacks import ProviderFallback
from autotube.domain.quality import ScoreItem
from autotube.domain.run_parts import Artifact
from autotube.domain.srt import SrtEntry
from autotube.pipelines.narrated_video.art.stand_ins import STAND_IN_FOR
from autotube.pipelines.narrated_video.artifacts import EPISODE, Role, with_role
from autotube.pipelines.narrated_video.plugin import KidsStoryPipeline
from autotube.pipelines.narrated_video.scoring.content_items import (
    character_consistency,
    reading_level,
)
from autotube.pipelines.narrated_video.scoring.inputs import ScoreInputs, gathered
from autotube.pipelines.narrated_video.scoring.measures import (
    SubtitleRules,
    range_score,
    subtitle_track,
)
from autotube.pipelines.narrated_video.scoring.output_items import (
    completeness,
    loudness,
    metadata_limits,
    real_pictures,
)
from autotube.pipelines.narrated_video.scoring.timing_items import (
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
        "real_pictures",
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
        "real_pictures",
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


def scene_pictures(artifacts: Sequence[Artifact]) -> list[Artifact]:
    return [a for a in with_role(artifacts, Role.VISUAL, variant=EPISODE) if "scene" in a.meta]


def with_stand_ins_at(inputs: ScoreInputs, count: int) -> ScoreInputs:
    replaced = {a.id for a in scene_pictures(inputs.artifacts)[:count]}
    stand_in = {STAND_IN_FOR: ["mflux"]}
    artifacts = tuple(
        a.model_copy(update={"meta": {**a.meta, **stand_in}}) if a.id in replaced else a
        for a in inputs.artifacts
    )
    return replace(inputs, artifacts=artifacts)


@pytest.mark.parametrize("count", [0, 1])
def test_real_pictures_scores_the_share_drawn_by_the_chosen_model(
    inputs: ScoreInputs, count: int
) -> None:
    total = len(scene_pictures(inputs.artifacts))
    item = required(real_pictures(with_stand_ins_at(inputs, count)))
    assert item.score == pytest.approx(100 * (total - count) / total)
    assert item.detail == (
        f"{count} of {total} episode pictures are stand-ins drawn after mflux failed"
        if count
        else f"all {total} episode pictures came from the chosen image model"
    )


@pytest.mark.parametrize(("used", "marked"), [("fake-image", True), ("other-image", False)])
def test_the_art_stage_marks_pictures_drawn_after_an_image_fallback(
    tmp_path: Path, used: str, marked: bool
) -> None:
    gated = ProviderFallback(capability=Capability.IMAGE, failed="mflux", used=used, reason="403")
    rig = finished(tmp_path, FakeProviders(fallen_back=[gated]), ("en",))
    pictures = scene_pictures(rig.artifacts)
    assert pictures and all((STAND_IN_FOR in a.meta) is marked for a in pictures)
    assert not any(STAND_IN_FOR in a.meta for a in with_role(rig.artifacts, Role.CANDIDATE))
    item = required(real_pictures(gathered(rig.context())))
    assert item.score == (0 if marked else 100)
