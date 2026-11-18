from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from PIL import Image
from pydantic import ValidationError

from automator.domain.capabilities import ImageRequest, MotionRequest
from automator.domain.image_style import ImageStyleHints, Outline, Texture
from automator.infrastructure.providers.image.offline_image import OfflineImage, OfflineImageOptions
from automator.infrastructure.providers.image.scene_palette import Palette
from automator.infrastructure.providers.image.style_palette import (
    hinted_palette,
    ink_for,
    luminance,
)
from automator.infrastructure.providers.motion.pan_zoom_filter import PanZoomTuning, pan_zoom_filter
from tests.unit.infrastructure.providers.fakes import make_context

WARM = ("#F4A259", "#E9C46A", "#E76F51", "#9C4A2F", "#F7D08A")
COOL = ("#8ECAE6", "#A8DADC", "#457B9D", "#1D3557", "#2EC4B6")
DARK_SKY = ("#2F4F3F", "#46685A", "#06D6A0", "#FFD166", "#EF476F")


def drawn(
    tmp_path: Path,
    name: str,
    hints: ImageStyleHints | None,
    seed: int = 3,
    width: int = 160,
    prompt: str = "a fox by the river",
) -> np.ndarray:
    adapter = OfflineImage(OfflineImageOptions(supersample=1), make_context(tmp_path))
    request = ImageRequest(
        prompt=prompt, width=width, height=width * 9 // 16, seed=seed, style=hints
    )
    with Image.open(adapter.generate(request, tmp_path / f"{name}.png")) as image:
        return np.asarray(image.convert("RGB"), dtype=np.int32)


def hints(
    palette: tuple[str, ...] = WARM,
    outline: Outline = Outline.NONE,
    texture: Texture = Texture.SMOOTH,
) -> ImageStyleHints:
    return ImageStyleHints(palette=palette, outline=outline, texture=texture)


def test_the_offline_picture_paints_with_the_hinted_palette(tmp_path: Path) -> None:
    warm, cool = drawn(tmp_path, "warm", hints(WARM)), drawn(tmp_path, "cool", hints(COOL))
    warm_red, warm_blue = warm[..., 0].mean(), warm[..., 2].mean()
    cool_red, cool_blue = cool[..., 0].mean(), cool[..., 2].mean()
    assert warm_red > warm_blue and cool_blue > cool_red


def test_a_styled_offline_picture_is_deterministic_for_a_seed(tmp_path: Path) -> None:
    styled = hints(outline=Outline.BOLD, texture=Texture.PAPER)
    first, again = drawn(tmp_path, "a", styled), drawn(tmp_path, "b", styled)
    other = drawn(tmp_path, "c", styled, seed=4)
    assert np.array_equal(first, again) and not np.array_equal(first, other)


def dark_share(picture: np.ndarray) -> float:
    return float((picture.sum(axis=2) < 150).mean())


def test_outline_weight_draws_more_ink(tmp_path: Path) -> None:
    shares = [
        dark_share(drawn(tmp_path, weight.value, hints(outline=weight), width=640))
        for weight in Outline
    ]
    assert shares[0] < shares[1] < shares[2]


@pytest.fixture(scope="module")
def smooth_picture(tmp_path_factory: pytest.TempPathFactory) -> np.ndarray:
    return drawn(tmp_path_factory.mktemp("smooth"), "smooth", hints())


@pytest.mark.parametrize("texture", [Texture.PAPER, Texture.GRAIN, Texture.CLAY, Texture.PIXEL])
def test_every_texture_changes_the_smooth_picture(
    tmp_path: Path, texture: Texture, smooth_picture: np.ndarray
) -> None:
    assert not np.array_equal(
        smooth_picture, drawn(tmp_path, texture.value, hints(texture=texture))
    )


def test_pixel_texture_keeps_only_palette_colours(tmp_path: Path) -> None:
    picture = drawn(tmp_path, "pixel", hints(texture=Texture.PIXEL))
    assert len(np.unique(picture.reshape(-1, 3), axis=0)) <= 8


def test_hints_without_colours_keep_the_derived_palette(tmp_path: Path) -> None:
    plain = drawn(tmp_path, "plain", None)
    assert np.array_equal(plain, drawn(tmp_path, "empty", ImageStyleHints()))


def brightness(picture: np.ndarray) -> float:
    return float(picture.mean())


def test_with_hints_night_comes_from_the_scene_not_the_art_direction(tmp_path: Path) -> None:
    day = drawn(tmp_path, "day", hints(), prompt="a fox")
    styled = hints().model_copy(update={"scene_text": "a fox in a sunny meadow"})
    art_night_words = "moonlight, stars, dream, sleep, bedtime. a fox"
    art = drawn(tmp_path, "art", styled, prompt=art_night_words)
    assert brightness(art) > brightness(day) * 0.9
    starry = hints().model_copy(update={"scene_text": "a fox under the stars"})
    assert brightness(drawn(tmp_path, "scene", starry)) < brightness(day) * 0.7


def test_a_night_hint_paints_night_whatever_the_scene(tmp_path: Path) -> None:
    day = drawn(tmp_path, "day", hints())
    asked = hints().model_copy(update={"night": True, "scene_text": "a sunny meadow"})
    assert brightness(drawn(tmp_path, "asked", asked)) < brightness(day) * 0.7


def test_without_hints_night_still_comes_from_the_prompt(tmp_path: Path) -> None:
    day = drawn(tmp_path, "day", None)
    assert brightness(drawn(tmp_path, "moon", None, prompt="a fox by moonlight")) < brightness(day)


def test_a_dark_backdrop_gets_light_ink_and_a_light_one_dark_ink() -> None:
    dark = ink_for(Outline.THIN, hinted_palette(hints(DARK_SKY), night=False))
    light = ink_for(Outline.BOLD, hinted_palette(hints(COOL), night=False))
    assert dark is not None and luminance(dark.color) > 0.5
    assert light is not None and luminance(light.color) < 0.2
    assert ink_for(Outline.NONE, hinted_palette(hints(), night=False)) is None


def test_a_night_prompt_darkens_the_hinted_palette() -> None:
    day: Palette = hinted_palette(hints(WARM), night=False)
    night = hinted_palette(hints(WARM), night=True)
    assert night.night and luminance(night.sky_top) < luminance(day.sky_top)


def held(rate: int | None) -> MotionRequest:
    return MotionRequest(
        image=Path("/in/still.png"),
        duration_seconds=2,
        width=320,
        height=180,
        fps=25,
        held_frame_rate=rate,
    )


@pytest.mark.parametrize(
    ("rate", "steps"), [(12, ["fps=12", "fps=25"]), (None, []), (25, []), (30, [])]
)
def test_pan_and_zoom_holds_frames_only_below_the_frame_rate(
    rate: int | None, steps: list[str]
) -> None:
    tuning = PanZoomTuning(max_zoom=0.3, supersample=1, crf=18, preset="fast")
    parts = pan_zoom_filter(held(rate), tuning).split(",")
    assert [part for part in parts if part.startswith("fps=")] == steps
    assert parts[-1] == "format=yuv420p"


def test_style_hints_accept_only_hex_colours() -> None:
    with pytest.raises(ValidationError):
        ImageStyleHints(palette=("red",))
