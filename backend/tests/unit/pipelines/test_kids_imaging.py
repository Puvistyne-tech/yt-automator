from __future__ import annotations

import random
from pathlib import Path

import pytest
from PIL import Image
from pydantic import ValidationError

from automator.pipelines.kids_story.art.imaging import (
    JpegBudget,
    covered_copy,
    qualities,
    saved_jpeg,
)
from automator.pipelines.kids_story.settings.thumbnail import ThumbnailSettings


def noisy(path: Path, size: tuple[int, int] = (640, 360)) -> Path:
    data = random.Random(7).randbytes(size[0] * size[1] * 3)
    Image.frombytes("RGB", size, data).save(path)
    return path


def budget(max_bytes: int, quality: int = 92, min_quality: int = 40) -> JpegBudget:
    return JpegBudget(max_bytes, quality, min_quality, downscale_step=0.5, min_width=160)


def width_of(path: Path) -> int:
    with Image.open(path) as image:
        return image.width


def test_qualities_step_down_to_the_lowest() -> None:
    assert qualities(budget(1, 92, 80)) == [92, 87, 82, 80]
    assert qualities(budget(1, 60, 60)) == [60]


def test_jpeg_keeps_the_best_quality_that_fits(tmp_path: Path) -> None:
    source = noisy(tmp_path / "noisy.png")
    roomy = saved_jpeg(source, tmp_path / "roomy.jpg", budget(10_000_000))
    assert (
        roomy == (tmp_path / "roomy.jpg").stat().st_size and width_of(tmp_path / "roomy.jpg") == 640
    )
    tight = saved_jpeg(source, tmp_path / "tight.jpg", budget(roomy // 2, 92, 10))
    assert tight <= roomy // 2 and width_of(tmp_path / "tight.jpg") == 640


def test_jpeg_shrinks_when_the_lowest_quality_is_still_too_big(tmp_path: Path) -> None:
    source = noisy(tmp_path / "noisy.png")
    at_lowest = saved_jpeg(source, tmp_path / "full.jpg", budget(10_000_000, 40, 40))
    size = saved_jpeg(source, tmp_path / "small.jpg", budget(at_lowest // 2))
    assert size <= at_lowest // 2 and width_of(tmp_path / "small.jpg") in {320, 160}


def test_jpeg_that_never_fits_stops_at_the_minimum_width(tmp_path: Path) -> None:
    source = noisy(tmp_path / "noisy.png")
    size = saved_jpeg(source, tmp_path / "tiny.jpg", budget(10))
    assert size == (tmp_path / "tiny.jpg").stat().st_size and size > 10
    assert width_of(tmp_path / "tiny.jpg") == 160
    assert (tmp_path / "tiny.jpg").read_bytes()[:2] == b"\xff\xd8"


def test_covered_copy_fills_the_size_or_reports_failure(tmp_path: Path) -> None:
    source = noisy(tmp_path / "wide.png")
    made = covered_copy(source, tmp_path / "tall.png", (90, 160), 0.0)
    assert made is not None
    with Image.open(made) as image:
        assert image.size == (90, 160)
    broken = tmp_path / "broken.png"
    broken.write_bytes(b"nope")
    assert covered_copy(broken, tmp_path / "x.png", (10, 10), 0.5) is None


def test_thumbnail_quality_range_is_checked() -> None:
    with pytest.raises(ValidationError, match="lowest thumbnail quality"):
        ThumbnailSettings(jpeg_quality=50, min_jpeg_quality=60)
