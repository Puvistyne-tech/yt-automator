from __future__ import annotations

from pathlib import Path

import pytest

from autotube.pipelines.narrated_video.art import lettering
from autotube.pipelines.narrated_video.text.scripts import script_language
from tests.fixtures.kids_data import StageRig, meta_of, quick_settings, run_chain, with_font
from tests.fixtures.kids_pictures import corner_is_solid, is_solid, scene_visual_files

TAMIL_MARK = "இரவுக் கதைகள்"


def visual_files(rig: StageRig, variant: str) -> list[Path]:
    return scene_visual_files(rig.root, meta_of(rig, "visual"), variant)


LATIN_MARK = "Bedtime tales"


def badge_on(text: str = LATIN_MARK) -> dict[str, object]:
    return {"overlay_series_badge": True, "badge_text": text}


def badge_run(root: Path, fonts: dict[str, list[str]], text: str = LATIN_MARK) -> StageRig:
    visuals = badge_on(text)
    settings = quick_settings(visuals=visuals, thumbnail={"font_files": fonts})
    return run_chain(StageRig(root, settings=settings), "art")


@pytest.mark.parametrize(
    ("text", "language"),
    [(TAMIL_MARK, "ta"), (LATIN_MARK, "en"), ("Kavin கவின்", "ta"), ("", "en"), ("௧", "ta")],
)
def test_script_language_follows_the_tamil_block(text: str, language: str) -> None:
    assert script_language(text) == language


@pytest.mark.usefixtures("shaping")
def test_brand_mark_is_drawn_after_cropping_on_every_variant(
    tmp_path: Path, font_file: Path
) -> None:
    settings = with_font(font_file, visuals=badge_on())
    rig = run_chain(StageRig(tmp_path, settings=settings), "art")
    for path in [*visual_files(rig, "episode"), *visual_files(rig, "short")]:
        assert path.name.endswith("-badge.png") and not corner_is_solid(path)
    assert is_solid(tmp_path / "art" / "scene-0-short.png")
    assert is_solid(tmp_path / "art" / "scene-0-c0.png")


@pytest.mark.usefixtures("shaping")
def test_tamil_brand_mark_uses_the_tamil_fonts(tmp_path: Path, font_file: Path) -> None:
    rig = badge_run(tmp_path / "ta", {"en": [], "ta": [str(font_file)]}, TAMIL_MARK)
    for path in visual_files(rig, "episode"):
        assert path.name.endswith("-badge.png") and not corner_is_solid(path)
    latin_only = badge_run(tmp_path / "en", {"en": [str(font_file)], "ta": []}, TAMIL_MARK)
    assert all("badge" not in path.name for path in visual_files(latin_only, "episode"))


def test_tamil_brand_mark_is_skipped_without_shaping(
    tmp_path: Path, font_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(lettering, "shaping_available", lambda: False)
    rig = badge_run(tmp_path, {"en": [str(font_file)], "ta": [str(font_file)]}, TAMIL_MARK)
    assert all("badge" not in path.name for path in visual_files(rig, "episode"))
    assert any("brand mark skipped" in line for line in rig.logs)


def test_brand_mark_without_a_font_is_skipped_and_logged(tmp_path: Path) -> None:
    rig = badge_run(tmp_path, {"en": [], "ta": []})
    assert all("badge" not in path.name for path in visual_files(rig, "episode"))
    assert any("brand mark skipped" in line for line in rig.book.warnings())


@pytest.mark.parametrize(
    "visuals",
    [{**badge_on(), "overlay_series_badge": False}, badge_on("  "), {"overlay_series_badge": True}],
)
def test_no_brand_mark_keeps_the_chosen_picture(
    tmp_path: Path, font_file: Path, visuals: dict[str, object]
) -> None:
    settings = with_font(font_file, visuals=visuals)
    rig = run_chain(StageRig(tmp_path, settings=settings), "art")
    names = [path.name for path in visual_files(rig, "episode")]
    assert names and all("-c" in name and "badge" not in name for name in names)
    assert all(path.name.endswith("-short.png") for path in visual_files(rig, "short"))
    assert not any("brand mark skipped" in line for line in rig.logs)
