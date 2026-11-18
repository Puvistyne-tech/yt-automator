from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from automator.domain.image_style import Texture
from automator.pipelines.kids_story.art.cards import lettering_for
from automator.pipelines.kids_story.art.prompts import judge_request, motion_prompt
from automator.pipelines.kids_story.settings.base import Placement
from automator.pipelines.kids_story.stages.motion import held_rate
from automator.pipelines.kids_story.story.model import StoryScene
from automator.pipelines.kids_story.styles.library import style_named
from tests.fixtures.kids_data import StageRig, meta_of, quick_settings, run_chain, smart_writer
from tests.fixtures.kids_fakes import FakeProviders


def styled_run(root: Path, until: str, **look: Any) -> StageRig:
    settings = quick_settings(look=look, visuals={"short_art_mode": "native"})
    rig = StageRig(root, settings=settings, providers=FakeProviders(writer=smart_writer()))
    return run_chain(rig, until)


def style_prompt(style_id: str) -> str:
    entry = style_named(style_id)
    assert entry is not None
    return entry.prompt


def test_every_picture_prompt_carries_the_resolved_style(tmp_path: Path) -> None:
    rig = styled_run(tmp_path, "art", visual_style="pixel_art", lighting="moonlight")
    requests = rig.providers.images.requests
    sizes = {(request.width, request.height) for request in requests}
    assert {(1280, 720), (720, 1280), (256, 256), (640, 360)} <= sizes
    for request in requests:
        assert request.prompt.startswith(style_prompt("pixel_art"))
        assert "gentle silvery moonlight" in request.prompt
        assert request.style is not None and request.style.texture is Texture.PIXEL
        assert "smooth gradients" in request.negative_prompt


def test_realistic_styles_keep_the_child_safety_wording(tmp_path: Path) -> None:
    rig = styled_run(tmp_path, "art", visual_style="realistic_photo")
    scenes = [r for r in rig.providers.images.requests if (r.width, r.height) == (1280, 720)]
    assert scenes and all("Child-friendly composition" in r.prompt for r in scenes)
    assert all("violence, weapons" in r.negative_prompt for r in scenes)


def test_the_resolved_style_is_saved_and_logged_once(tmp_path: Path) -> None:
    rig = styled_run(tmp_path, "art", visual_style="claymation")
    [record] = meta_of(rig, "style")
    saved = json.loads((tmp_path / record.filename).read_text(encoding="utf-8"))
    assert saved["style_id"] == "claymation" and saved["texture"] == "clay"
    assert saved["motion"]["held_frame_rate"] == 12
    lines = [line for line in rig.logs if line.startswith("visual style:")]
    assert lines == [
        "visual style: Claymation (claymation); palette "
        + ", ".join(saved["palette"])
        + "; outline none, texture clay, held frames at 12 per second"
    ]


def test_the_picture_judge_is_told_the_resolved_style(tmp_path: Path) -> None:
    settings = quick_settings(look={"visual_style": "anime"})
    scene = StoryScene(narration="Hi.", visual="a fox")
    assert style_prompt("anime") in judge_request(settings, scene, [tmp_path]).prompt


def test_motion_follows_the_style_held_frames_and_card_camera(tmp_path: Path) -> None:
    rig = styled_run(tmp_path, "motion", visual_style="shadow_puppet")
    clips = meta_of(rig, "clip")
    requests = rig.providers.motion.requests
    by_key = {str(c.meta["visual_key"]): r for c, r in zip(clips, requests, strict=True)}
    assert {request.held_frame_rate for request in requests} == {12}
    assert by_key["card-intro-en@episode"].camera.value == "pan_right"
    assert by_key["scene-1@episode"].intensity == 0.3
    assert by_key["scene-1@episode"].prompt.endswith(
        "Camera: puppets gliding sideways across a lit screen."
    )
    assert {clip.meta["held_frame_rate"] for clip in clips} == {12}


def test_a_held_rate_only_applies_below_the_frame_rate() -> None:
    assert held_rate(12, 30) == 12
    assert held_rate(30, 30) is None
    assert held_rate(None, 30) is None


def test_the_motion_prompt_adds_the_camera_feel_only_when_given() -> None:
    assert motion_prompt(None).endswith("no sudden changes.")
    assert motion_prompt(None, "slow drift").endswith("Camera: slow drift.")


def test_cards_and_thumbnails_letter_in_the_style_colours() -> None:
    styled = quick_settings(look={"visual_style": "comic_book"})
    lettering = lettering_for(styled, ["Hi"], "en", Placement.CENTER, 0.1)
    assert (lettering.color, lettering.outline) == ("#FFD60A", "#111111")
    plain = quick_settings(look={"visual_style": "comic_book", "use_style_lettering": False})
    kept = lettering_for(plain, ["Hi"], "en", Placement.CENTER, 0.1)
    assert (kept.color, kept.outline) == ("#FFFFFF", "#3A2A1A")
