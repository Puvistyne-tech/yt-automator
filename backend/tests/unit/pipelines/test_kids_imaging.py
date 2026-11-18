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
    shuffle = random.Random(7)
    data = bytes(shuffle.randrange(256) for _ in range(size[0] * size[1] * 3))
    Image.frombytes("RGB", size, data).save(path)
    return path


def test_qualities_step_down_to_the_lowest() -> None:
    assert qualities(JpegBudget(max_bytes=1, quality=92, min_quality=80)) == [92, 87, 82, 80]
    assert qualities(JpegBudget(max_bytes=1, quality=60, min_quality=60)) == [60]


def test_jpeg_keeps_the_best_quality_that_fits(tmp_path: Path) -> None:
    source = noisy(tmp_path / "noisy.png")
    roomy = saved_jpeg(source, tmp_path / "roomy.jpg", JpegBudget(10_000_000, 92, 40))
    assert roomy == 92
    full_size = (tmp_path / "roomy.jpg").stat().st_size
    limit = full_size // 2
    tight = saved_jpeg(source, tmp_path / "tight.jpg", JpegBudget(limit, 92, 10))
    assert 10 <= tight < 92 and (tmp_path / "tight.jpg").stat().st_size <= limit


def test_jpeg_that_never_fits_is_saved_at_the_lowest_quality(tmp_path: Path) -> None:
    source = noisy(tmp_path / "noisy.png")
    quality = saved_jpeg(source, tmp_path / "small.jpg", JpegBudget(10, 50, 30))
    assert quality == 30 and (tmp_path / "small.jpg").read_bytes()[:2] == b"\xff\xd8"


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
