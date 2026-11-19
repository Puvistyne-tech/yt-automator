from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from autotube.domain.model_base import JsonObject
from autotube.domain.run_enums import ArtifactKind
from autotube.domain.run_parts import Artifact
from autotube.pipelines.narrated_video.scoring.content_items import moral_and_refrain
from autotube.pipelines.narrated_video.scoring.inputs import ScoreInputs
from autotube.pipelines.narrated_video.scoring.timing_items import episode_duration, subtitle_timing
from autotube.pipelines.narrated_video.story.model import Story
from autotube.pipelines.narrated_video.timeline.voices import VoiceLine
from tests.fixtures.kids_data import quick_settings, story

TARGET = {"target_duration_seconds": 100, "duration_tolerance_seconds": 10}


def made(role: str, language: str, filename: str = "x", **meta: Any) -> Artifact:
    return Artifact(
        id=f"{role}-{language}",
        kind=ArtifactKind.TEXT,
        stage_id="assemble",
        language=language,
        variant="episode",
        filename=filename,
        media_type="text/plain",
        size_bytes=1,
        meta={"role": role, **meta},
    )


def final_video(language: str, keys: list[str], seconds: float = 200.0) -> Artifact:
    timeline: list[JsonObject] = [{"key": key} for key in keys]
    return made("final_video", language, duration_seconds=seconds, timeline=list(timeline))


def line(key: str, seconds: float, text: str = "hi") -> VoiceLine:
    return VoiceLine(segment=key, filename=f"{key}.wav", seconds=seconds, text=text)


def inputs(
    root: Path,
    artifacts: list[Artifact],
    voices: dict[str, dict[str, VoiceLine]],
    stories: dict[str, Story] | None = None,
    **sections: dict[str, Any],
) -> ScoreInputs:
    return ScoreInputs(
        settings=quick_settings(**sections),
        languages=("en", "ta"),
        artifacts=tuple(artifacts),
        workspace=root,
        stories=stories or {},
        voices=voices,
        media=None,
    )


@pytest.mark.parametrize(
    ("first", "second", "score"),
    [(40.0, 50.0, 100.0), (50.0, 60.0, 100.0), (40.0, 49.0, 98.0), (50.0, 61.0, 98.0)],
)
def test_episode_length_scores_scene_narration_only(
    tmp_path: Path, first: float, second: float, score: float
) -> None:
    keys = ["intro", "scene-0", "scene-1", "outro", "hook"]
    english = {
        "intro": line("intro", 30.0),
        "scene-0": line("scene-0", first),
        "scene-1": line("scene-1", second),
        "outro": line("outro", 30.0),
        "hook": line("hook", 30.0),
    }
    tamil = {"scene-0": line("scene-0", 500.0)}
    built = inputs(tmp_path, [final_video("en", keys)], {"en": english, "ta": tamil}, story=TARGET)
    item = episode_duration(built)
    assert item is not None and item.score == pytest.approx(score)
    assert item.detail.startswith("en ") and "ta " not in item.detail


def ending_without_moral_or_refrain(draft: Story) -> Story:
    scenes = [
        scene.model_copy(update={"narration": "Kavin waved goodbye to everyone."})
        for scene in draft.scenes
    ]
    return draft.model_copy(update={"scenes": scenes})


@pytest.mark.parametrize(
    ("points", "broken", "score"), [(50.0, False, 50.0), (20.0, False, 80.0), (100.0, True, 0.0)]
)
def test_points_lost_per_problem(tmp_path: Path, points: float, broken: bool, score: float) -> None:
    draft = ending_without_moral_or_refrain(story()) if broken else story()
    refrain = {"en": "Hooray for friends!", "ta": "ஆஹா!"}
    built = inputs(
        tmp_path,
        [],
        {},
        {"en": draft},
        quality={"points_lost_per_problem": points},
        series={"refrain": refrain},
    )
    item = moral_and_refrain(built)
    assert item is not None and item.score == score


def captions(root: Path, blocks: list[tuple[str, str, str]]) -> Artifact:
    content = "\n\n".join(
        f"{number}\n{start} --> {end}\n{text}"
        for number, (start, end, text) in enumerate(blocks, start=1)
    )
    (root / "en.srt").write_text(content, encoding="utf-8")
    return made("captions", "en", "en.srt")


OVERLAPPING = [
    ("00:00:00,000", "00:00:01,500", "one two"),
    ("00:00:01,000", "00:00:02,000", "three four"),
]
PARTIAL = [("00:00:00,000", "00:00:01,000", "one two")]


@pytest.mark.parametrize(
    ("blocks", "quality", "score"),
    [
        (OVERLAPPING, {"subtitle_overlap_penalty": 0.9, "subtitle_out_of_bounds_penalty": 0.1}, 90),
        (OVERLAPPING, {"subtitle_overlap_penalty": 0.1, "subtitle_out_of_bounds_penalty": 0.9}, 10),
        (PARTIAL, {"subtitle_min_coverage": 1.0}, 50),
    ],
)
def test_subtitle_settings_shape_the_timing_score(
    tmp_path: Path, blocks: list[tuple[str, str, str]], quality: dict[str, float], score: float
) -> None:
    voices = {"en": {"scene-0": line("scene-0", 2.0, "one two three four")}}
    artifacts = [final_video("en", ["scene-0"], 10.0), captions(tmp_path, blocks)]
    item = subtitle_timing(inputs(tmp_path, artifacts, voices, quality=quality))
    assert item is not None and item.score == pytest.approx(score)
