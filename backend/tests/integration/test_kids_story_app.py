from __future__ import annotations

import json
import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from autotube.domain.channels import Privacy
from autotube.infrastructure.config import RuntimeConfig
from autotube.main import Overrides, create_app
from tests.fixtures.fake_runtime import InMemorySecrets
from tests.fixtures.fake_youtube import FakeYouTube
from tests.fixtures.ffmpeg_filters import ffmpeg_has
from tests.unit.api.client import Api, ok

pytestmark = [
    pytest.mark.integration,
    pytest.mark.slow,
    pytest.mark.skipif(
        not ffmpeg_has("ass", "zoompan", "loudnorm"),
        reason="needs ffmpeg and ffprobe with the ass, zoompan and loudnorm filters",
    ),
]
TARGETS = {"en": ["episode", "short"], "ta": ["episode", "short"]}
SIZES = {"episode": (640, 360), "short": (360, 640)}
RUN_SECONDS = 120.0
SMALL_SETTINGS: dict[str, Any] = {
    "episode": {
        "resolution": "640x360",
        "fps": 12,
        "intro_card": False,
        "outro_card": False,
        "scene_lead_in_seconds": 0,
        "scene_tail_seconds": 0,
        "min_scene_seconds": 0.5,
        "fade_seconds": 0,
    },
    "voice": {"speed": 1.5, "include_intro": False, "include_outro": False},
    "short": {"resolution": "360x640", "max_scenes": 1, "hook_line": False},
    "music": {"enabled": False},
    "sound_effects": {"enabled": False},
    "subtitles": {"font_size": 24, "short_font_size": 30},
    "thumbnail": {"width": 640, "height": 360},
    "visuals": {
        "image_candidates": 1,
        "hero_candidates": 1,
        "hero_scene_count": 0,
        "character_sheets": False,
        "use_vision_judge": False,
        "sheet_size": 256,
        "motion_intensity": 0,
        "hero_motion_intensity": 0,
    },
}
FASTEST_ENCODING: list[dict[str, Any]] = [
    {
        "capability": "media",
        "chain": [
            {
                "provider_id": "ffmpeg",
                "options": {
                    "preset": "ultrafast",
                    "two_pass_loudness": False,
                    "audio_bitrate": "32k",
                    "sample_rate": 22050,
                },
            }
        ],
    },
    {
        "capability": "motion",
        "chain": [{"provider_id": "ffmpeg_pan_zoom", "options": {"preset": "ultrafast"}}],
    },
]


@pytest.fixture
def youtube() -> FakeYouTube:
    return FakeYouTube()


@pytest.fixture
def config(tmp_path: Path) -> RuntimeConfig:
    return RuntimeConfig(
        data_dir=tmp_path / "data",
        web_dist_dir=tmp_path / "no-dist",
        worker_poll_seconds=0.05,
        scheduler_tick_seconds=3600,
    )


@pytest.fixture
def api(config: RuntimeConfig, youtube: FakeYouTube) -> Iterator[Api]:
    overrides = Overrides(youtube=youtube, secrets=InMemorySecrets())
    with TestClient(create_app(config, overrides), follow_redirects=False) as client:
        yield Api(client, client.app.state.runtime)  # type: ignore[attr-defined]


def reviewed_run(api: Api) -> dict[str, Any]:
    ok(api.client.put("/api/providers", json=FASTEST_ENCODING))
    channel_id = api.channel()
    targets = [
        {"channel_id": channel_id, "language": language, "variants": variants}
        for language, variants in TARGETS.items()
    ]
    automation = api.automation(
        channel_id,
        name="Bedtime tales",
        pipeline_type="kids_story",
        settings=SMALL_SETTINGS,
        languages=list(TARGETS),
        targets=targets,
        review_policy={"mode": "always"},
    )
    run = api.start(automation["id"])
    return api.wait_for(run["id"], "awaiting_review", "failed", seconds=RUN_SECONDS)


def final_videos(run: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    return {
        (artifact["language"], artifact["variant"]): artifact
        for artifact in run["artifacts"]
        if artifact["meta"].get("role") == "final_video"
    }


def probed(api: Api, run_id: str, artifact: dict[str, Any], folder: Path) -> dict[str, Any]:
    response = api.client.get(f"/api/runs/{run_id}/artifacts/{artifact['id']}")
    assert response.status_code == 200, response.text
    path = folder / f"{artifact['language']}-{artifact['variant']}.mp4"
    path.write_bytes(response.content)
    command = ["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)]
    found: dict[str, Any] = json.loads(
        subprocess.run(command, capture_output=True, text=True, check=True).stdout
    )
    return found


def check_video(api: Api, run_id: str, artifact: dict[str, Any], folder: Path) -> float:
    probe = probed(api, run_id, artifact, folder)
    kinds = {stream["codec_type"]: stream for stream in probe["streams"]}
    assert set(kinds) == {"video", "audio"}
    size = (kinds["video"]["width"], kinds["video"]["height"])
    assert size == SIZES[artifact["variant"]]
    seconds = float(probe["format"]["duration"])
    assert seconds == pytest.approx(artifact["meta"]["planned_seconds"], abs=1.0)
    return seconds


def check_uploads(youtube: FakeYouTube) -> None:
    assert len(youtube.uploads) == 4
    assert all(upload.made_for_kids for upload in youtube.uploads)
    assert {upload.privacy for upload in youtube.uploads} == {Privacy.PRIVATE}
    assert {upload.default_language for upload in youtube.uploads} == {"en", "ta"}
    assert {upload.category_id for upload in youtube.uploads} == {"1"}
    assert all("#KidsStories" in upload.description.split() for upload in youtube.uploads)


def test_kids_story_runs_through_the_real_app(
    api: Api, youtube: FakeYouTube, config: RuntimeConfig, tmp_path: Path
) -> None:
    listed = ok(api.client.get("/api/pipelines"))
    kids = next(pipeline for pipeline in listed if pipeline["type_id"] == "kids_story")
    assert kids["settings_schema"]["properties"]
    run = reviewed_run(api)
    assert run["status"] == "awaiting_review", run["error"]
    assert 0 < run["score"] <= 100
    videos = final_videos(run)
    assert set(videos) == {(lang, variant) for lang, kinds in TARGETS.items() for variant in kinds}
    seconds = {key: check_video(api, run["id"], video, tmp_path) for key, video in videos.items()}
    assert seconds["en", "short"] < seconds["en", "episode"]
    workspace = config.data_dir / "runs" / run["id"] / "workspace"
    assert (workspace / "videos" / "ta-short.ass").is_file()
    ok(api.client.post(f"/api/runs/{run['id']}/review", json={"decision": "approved"}))
    published = ok(api.client.post(f"/api/runs/{run['id']}/publish"))
    assert published["status"] == "published", published["error"]
    assert [upload["status"] for upload in published["uploads"]] == ["done"] * 4
    check_uploads(youtube)
