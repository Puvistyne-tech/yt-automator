from __future__ import annotations

import random
from pathlib import Path

import pytest
from PIL import Image

from autotube.domain.capabilities import ImageRequest
from autotube.pipelines.kids_story.art import lettering
from autotube.pipelines.kids_story.art.cards import lettering_for
from autotube.pipelines.kids_story.settings.base import Placement
from tests.fixtures.kids_data import StageRig, meta_of, quick_settings, run_chain, with_font
from tests.fixtures.kids_fakes import FakeImages, FakeProviders
from tests.fixtures.kids_pictures import is_solid


def picture(path: Path, size: tuple[int, int] = (320, 180)) -> Path:
    Image.new("RGB", size, (40, 120, 180)).save(path)
    return path


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
        assert path.stat().st_size == item.meta["bytes"]
        assert path.stat().st_size <= 100_000
    assert not list((tmp_path / "package").glob("*-lettered.png"))
    assert not any("narrowest allowed width" in line for line in rig.logs)


class NoisyThumbnails(FakeImages):
    def generate(self, request: ImageRequest, output: Path) -> Path:
        if request.width != 1920:
            return super().generate(request, output)
        self.requests.append(request)
        noise = random.Random(request.seed).randbytes(request.width * request.height * 3)
        Image.frombytes("RGB", (request.width, request.height), noise).save(output)
        return output


def test_a_thumbnail_too_big_at_the_narrowest_width_is_logged(tmp_path: Path) -> None:
    thumbnail = {"width": 1920, "height": 1080, "max_bytes": 100_000}
    limits = {**thumbnail, "min_width": 1920, "jpeg_quality": 40, "min_jpeg_quality": 10}
    settings = quick_settings(thumbnail=limits, short={"enabled": False})
    providers = FakeProviders(images=NoisyThumbnails())
    rig = run_chain(StageRig(tmp_path, settings=settings, languages=("en",), providers=providers))
    [item] = meta_of(rig, "thumbnail")
    assert int(str(item.meta["bytes"])) > 100_000
    assert any("narrowest allowed width" in line for line in rig.logs)


@pytest.mark.usefixtures("shaping")
def test_cards_are_lettered_with_an_available_font(tmp_path: Path, font_file: Path) -> None:
    rig = run_chain(StageRig(tmp_path, settings=with_font(font_file)), "art")
    cards = [item for item in meta_of(rig, "visual") if "card" in item.meta]
    assert len(cards) == 4 and all(item.meta["lettered"] is True for item in cards)
    plain = run_chain(StageRig(tmp_path / "plain"), "art")
    plain_cards = [item for item in meta_of(plain, "visual") if "card" in item.meta]
    assert {item.meta["lettered"] for item in plain_cards} == {False}
