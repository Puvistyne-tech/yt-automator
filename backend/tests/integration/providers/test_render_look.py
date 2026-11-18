from __future__ import annotations

import shutil
from pathlib import Path

import numpy
import pytest
from PIL import Image

from autotube.domain.capabilities import TimedClip, VideoComposition, WordTiming
from autotube.domain.video_look import (
    ScreenCorner,
    SubtitlePosition,
    SubtitleStyle,
    Transition,
    Watermark,
)
from autotube.infrastructure.providers.context import ProviderContext
from autotube.infrastructure.providers.media.ffmpeg_media import FfmpegMedia
from autotube.infrastructure.providers.media.ffmpeg_options import FfmpegOptions
from tests.fixtures.fake_runtime import InMemorySecrets
from tests.fixtures.fonts import embedded_font, embedded_font_family

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not (shutil.which("ffmpeg") and shutil.which("ffprobe")),
        reason="ffmpeg and ffprobe are needed to render video",
    ),
]
SIZE = (320, 180)
Pixel = tuple[int, int, int]
WORDS = (
    WordTiming(word="Hello", start_seconds=0.2, end_seconds=1.0),
    WordTiming(word="friends", start_seconds=1.2, end_seconds=2.6),
)


def still(folder: Path, name: str, colour: Pixel, size: tuple[int, int] = SIZE) -> Path:
    path = folder / f"{name}.png"
    Image.new("RGB", size, colour).save(path)
    return path


def look_video(folder: Path, karaoke: bool) -> VideoComposition:
    srt = folder / "words.srt"
    srt.write_text("1\n00:00:00,200 --> 00:00:03,000\nHello friends\n", encoding="utf-8")
    font = embedded_font(folder)
    style = SubtitleStyle(
        burn_in=True,
        font_family=embedded_font_family(),
        font_file=font,
        font_size=40,
        margin_bottom=10,
        karaoke=karaoke,
        position=SubtitlePosition.TOP,
        box=True,
        box_opacity=1.0,
        highlight_color="#FFD54A",
    )
    logo = Watermark(
        image=still(folder, "logo", (0, 200, 0), (40, 40)),
        corner=ScreenCorner.BOTTOM_LEFT,
        width_share=0.2,
        opacity=1.0,
        margin_share=0.05,
    )
    return VideoComposition(
        width=SIZE[0],
        height=SIZE[1],
        fps=24,
        visuals=(
            TimedClip(path=still(folder, "red", (220, 0, 0)), start_seconds=0, duration_seconds=2),
            TimedClip(
                path=still(folder, "blue", (0, 0, 220)), start_seconds=1.5, duration_seconds=2
            ),
        ),
        subtitles=srt,
        subtitle_style=style,
        subtitle_words=WORDS,
        fade_seconds=0,
        transition=Transition.CROSSFADE,
        watermark=logo,
    )


def frame_at(media: FfmpegMedia, video: Path, seconds: float, folder: Path) -> Image.Image:
    path = media.extract_frame(video, seconds, folder / f"frame-{seconds}.png")
    with Image.open(path) as opened:
        return opened.convert("RGB")


def pixel(frame: Image.Image, x: int, y: int) -> Pixel:
    red, green, blue = (int(value) for value in numpy.asarray(frame)[y, x][:3])
    return red, green, blue


def golden_pixels(frame: Image.Image) -> int:
    top = numpy.asarray(frame.crop((0, 0, SIZE[0], SIZE[1] // 2))).astype(int)
    red, green, blue = top[..., 0], top[..., 1], top[..., 2]
    return int(((red > 180) & (green > 140) & (blue < 120)).sum())


def rendered(folder: Path, karaoke: bool) -> tuple[FfmpegMedia, Path]:
    folder.mkdir()
    context = ProviderContext(secrets=InMemorySecrets(), data_dir=folder)
    media = FfmpegMedia(FfmpegOptions(two_pass_loudness=False), context)
    return media, media.compose_video(look_video(folder, karaoke), folder / "look.mp4")


def test_crossfade_logo_box_and_karaoke_reach_the_picture(tmp_path: Path) -> None:
    media, sung = rendered(tmp_path / "sung", karaoke=True)
    _, plain = rendered(tmp_path / "plain", karaoke=False)
    assert media.duration_seconds(sung) == pytest.approx(3.5, abs=0.1)
    middle = frame_at(media, sung, 1.75, tmp_path)
    red, _, blue = pixel(middle, SIZE[0] // 2, SIZE[1] - 20)
    assert red > 60 and blue > 60
    corner = pixel(frame_at(media, sung, 0.5, tmp_path), 30, SIZE[1] - 20)
    assert corner[1] > 150 and corner[0] < 80
    assert golden_pixels(frame_at(media, sung, 0.5, tmp_path)) > 20
    assert golden_pixels(frame_at(media, plain, 0.5, tmp_path)) == 0
