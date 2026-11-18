from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from automator.pipelines.kids_story.art import lettering
from automator.pipelines.kids_story.art.cards import lettering_for
from automator.pipelines.kids_story.settings.base import Placement
from tests.fixtures.kids_data import StageRig, meta_of, quick_settings, run_chain, with_font


def picture(path: Path, size: tuple[int, int] = (320, 180)) -> Path:
    Image.new("RGB", size, (40, 120, 180)).save(path)
    return path


def single_colour(image: Image.Image) -> bool:
    return image.convert("RGB").getcolors(maxcolors=1) is not None


def is_solid(path: Path) -> bool:
    with Image.open(path) as image:
        return single_colour(image)


def corner_is_solid(path: Path) -> bool:
    with Image.open(path) as image:
        return single_colour(image.crop((0, 0, image.width // 2, image.height // 3)))


@pytest.fixture
def shaping(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    monkeypatch.setattr(lettering, "shaping_available", lambda: True)
    return monkeypatch


def test_load_font_skips_missing_and_corrupt_files(tmp_path: Path, font_file: Path) -> None:
    corrupt = tmp_path / "corrupt.ttf"
    corrupt.write_bytes(b"not a font")
    assert lettering.load_font([str(tmp_path / "missing.ttf"), str(corrupt)], 20) is None
    assert lettering.load_font([str(corrupt), str(font_file)], 20) is not None


def test_lettering_fails_softly(
    tmp_path: Path, font_file: Path, shaping: pytest.MonkeyPatch
) -> None:
    settings = with_font(font_file)
    words = lettering_for(settings, ["Hello"], "en", Placement.BOTTOM, 0.2)
    broken = tmp_path / "broken.png"
    broken.write_bytes(b"not a picture")
    assert not lettering.lettered(broken, tmp_path / "out.png", words)
    source = picture(tmp_path / "plain.png")
    assert lettering.lettered(source, tmp_path / "ok.png", words)
    assert not is_solid(tmp_path / "ok.png")
    shaping.setattr(lettering, "shaping_available", lambda: False)
    tamil = lettering_for(settings, ["வணக்கம்"], "ta", Placement.TOP, 0.2)
    assert not lettering.lettered(source, tmp_path / "ta.png", tamil)
    assert lettering.lettered(source, tmp_path / "en.png", words)


@pytest.mark.parametrize(
    ("language", "shaped", "fonts", "title_text", "drawn", "logged"),
    [
        ("en", True, True, True, True, False),
        ("ta", True, True, True, True, False),
        ("ta", False, True, True, False, True),
        ("en", False, True, True, True, False),
        ("en", True, False, True, False, True),
        ("en", True, True, False, False, False),
    ],
)
def test_thumbnail_titles(
    tmp_path: Path,
    font_file: Path,
    shaping: pytest.MonkeyPatch,
    language: str,
    shaped: bool,
    fonts: bool,
    title_text: bool,
    drawn: bool,
    logged: bool,
) -> None:
    shaping.setattr(lettering, "shaping_available", lambda: shaped)
    sections = {"thumbnail": {"title_text": title_text}, "short": {"enabled": False}}
    settings = with_font(font_file, **sections) if fonts else quick_settings(**sections)
    rig = run_chain(StageRig(tmp_path, settings=settings, languages=(language,)))
    [thumbnail] = meta_of(rig, "thumbnail")
    assert thumbnail.meta["title_drawn"] is drawn
    assert any("no usable font" in line for line in rig.logs) is logged


def test_thumbnails_are_jpeg_within_the_size_limit(tmp_path: Path) -> None:
    settings = quick_settings(thumbnail={"max_bytes": 100_000})
    rig = run_chain(StageRig(tmp_path, settings=settings, languages=("en",)))
    for item in meta_of(rig, "thumbnail"):
        path = tmp_path / item.filename
        assert item.media_type == "image/jpeg" and path.suffix == ".jpg"
        assert path.read_bytes()[:3] == b"\xff\xd8\xff"
        assert path.stat().st_size <= 100_000
    assert not list((tmp_path / "package").glob("*-lettered.png"))


@pytest.mark.usefixtures("shaping")
def test_cards_are_lettered_with_an_available_font(tmp_path: Path, font_file: Path) -> None:
    rig = run_chain(StageRig(tmp_path, settings=with_font(font_file)), "art")
    cards = [item for item in meta_of(rig, "visual") if "card" in item.meta]
    assert len(cards) == 4 and all(item.meta["lettered"] is True for item in cards)
    plain = run_chain(StageRig(tmp_path / "plain"), "art")
    plain_cards = [item for item in meta_of(plain, "visual") if "card" in item.meta]
    assert {item.meta["lettered"] for item in plain_cards} == {False}


def visual_files(rig: StageRig, variant: str) -> list[Path]:
    return [
        rig.root / item.filename
        for item in meta_of(rig, "visual")
        if item.variant == variant and "scene" in item.meta
    ]


@pytest.mark.usefixtures("shaping")
def test_brand_mark_is_drawn_after_cropping_on_every_variant(
    tmp_path: Path, font_file: Path
) -> None:
    settings = with_font(font_file, visuals={"overlay_series_badge": True})
    rig = run_chain(StageRig(tmp_path, settings=settings), "art")
    for path in [*visual_files(rig, "episode"), *visual_files(rig, "short")]:
        assert path.name.endswith("-badge.png") and not corner_is_solid(path)
    assert is_solid(tmp_path / "art" / "scene-0-short.png")
    assert is_solid(tmp_path / "art" / "scene-0-c0.png")


def test_brand_mark_without_a_font_is_a_plain_copy(tmp_path: Path) -> None:
    settings = quick_settings(visuals={"overlay_series_badge": True})
    rig = run_chain(StageRig(tmp_path, settings=settings), "art")
    for path in visual_files(rig, "episode"):
        assert path.name.endswith("-badge.png") and is_solid(path)


@pytest.mark.parametrize("visuals", [{"overlay_series_badge": False}, {"badge_text": "  "}])
def test_no_brand_mark_keeps_the_chosen_picture(
    tmp_path: Path, font_file: Path, visuals: dict[str, object]
) -> None:
    settings = with_font(font_file, visuals={"overlay_series_badge": True, **visuals})
    rig = run_chain(StageRig(tmp_path, settings=settings), "art")
    names = [path.name for path in visual_files(rig, "episode")]
    assert names and all("-c" in name and "badge" not in name for name in names)
    assert all(path.name.endswith("-short.png") for path in visual_files(rig, "short"))
