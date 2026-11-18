from __future__ import annotations

import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from automator.domain.channels import Privacy
from automator.infrastructure.config import RuntimeConfig
from automator.main import Overrides, create_app
from tests.fixtures.fake_runtime import InMemorySecrets
from tests.fixtures.fake_youtube import FakeYouTube
from tests.unit.api.client import Api, ok

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not (shutil.which("ffmpeg") and shutil.which("ffprobe")),
        reason="ffmpeg and ffprobe are needed to render the story videos",
    ),
]
LANGUAGES = ("en", "ta")
VARIANTS = ("episode", "short")
RUN_SECONDS = 600.0
SMALL_SETTINGS: dict[str, Any] = {
    "episode": {
        "resolution": "1280x720",
        "fps": 12,
        "intro_card": False,
        "outro_card": False,
        "scene_lead_in_seconds": 0,
        "scene_tail_seconds": 0,
        "min_scene_seconds": 0.5,
        "fade_seconds": 0,
    },
    "voice": {"speed": 1.5, "include_intro": False, "include_outro": False},
    "short": {"resolution": "720x1280", "max_scenes": 1, "hook_line": False},
    "thumbnail": {"width": 640, "height": 360},
    "visuals": {
        "image_candidates": 1,
        "hero_candidates": 1,
        "hero_scene_count": 0,
        "character_sheets": False,
        "use_vision_judge": False,
        "sheet_size": 256,
    },
}


@pytest.fixture
def youtube() -> FakeYouTube:
    return FakeYouTube()


@pytest.fixture
def api(tmp_path: Path, youtube: FakeYouTube) -> Iterator[Api]:
    config = RuntimeConfig(
        data_dir=tmp_path / "data",
        web_dist_dir=tmp_path / "no-dist",
        worker_poll_seconds=0.05,
        scheduler_tick_seconds=3600,
    )
    overrides = Overrides(youtube=youtube, secrets=InMemorySecrets())
    with TestClient(create_app(config, overrides), follow_redirects=False) as client:
        yield Api(client, client.app.state.runtime)  # type: ignore[attr-defined]


def reviewed_run(api: Api) -> dict[str, Any]:
    channel_id = api.channel()
    targets = [
        {"channel_id": channel_id, "language": language, "variants": list(VARIANTS)}
        for language in LANGUAGES
    ]
    automation = api.automation(
        channel_id,
        name="Kutty Stories",
        pipeline_type="kids_story",
        settings=SMALL_SETTINGS,
        languages=list(LANGUAGES),
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


def downloaded_seconds(api: Api, run_id: str, artifact: dict[str, Any], folder: Path) -> float:
    response = api.client.get(f"/api/runs/{run_id}/artifacts/{artifact['id']}")
    assert response.status_code == 200, response.text
    path = folder / f"{artifact['language']}-{artifact['variant']}.mp4"
    path.write_bytes(response.content)
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(probe.stdout.strip())


def test_kids_story_runs_through_the_real_app(
    api: Api, youtube: FakeYouTube, tmp_path: Path
) -> None:
    run = reviewed_run(api)
    assert run["status"] == "awaiting_review", run["error"]
    assert 0 < run["score"] <= 100
    videos = final_videos(run)
    assert set(videos) == {(language, variant) for language in LANGUAGES for variant in VARIANTS}
    for video in videos.values():
        assert downloaded_seconds(api, run["id"], video, tmp_path) > 0
    ok(api.client.post(f"/api/runs/{run['id']}/review", json={"decision": "approved"}))
    published = ok(api.client.post(f"/api/runs/{run['id']}/publish"))
    assert published["status"] == "published", published["error"]
    assert [upload["status"] for upload in published["uploads"]] == ["done"] * 4
    assert len(youtube.uploads) == 4
    assert all(upload.made_for_kids for upload in youtube.uploads)
    assert {upload.privacy for upload in youtube.uploads} == {Privacy.PRIVATE}
