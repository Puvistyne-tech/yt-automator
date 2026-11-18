from __future__ import annotations

from pathlib import Path

from automator.domain.capabilities import SubtitleStyle
from automator.shared.errors import UpstreamFailure

LIBASS_DEFAULT_PLAY_HEIGHT = 288
OPTION_SPECIALS = ("\\", "'", ":")
GRAPH_SPECIALS = ("\\", "'", "[", "]", ",", ";")


def escaped(value: str, specials: tuple[str, ...]) -> str:
    for special in specials:
        value = value.replace(special, f"\\{special}")
    return value


def filter_path(path: Path) -> str:
    return escaped(escaped(str(path), OPTION_SPECIALS), GRAPH_SPECIALS)


def ass_color(hex_color: str) -> str:
    digits = hex_color.lstrip("#")
    if len(digits) != 6 or any(char not in "0123456789abcdefABCDEF" for char in digits):
        raise UpstreamFailure(f"subtitle colour {hex_color!r} is not #RRGGBB")
    red, green, blue = digits[0:2], digits[2:4], digits[4:6]
    return f"&H00{blue}{green}{red}".upper()


def style_scale(subtitles: Path, video_height: int) -> float:
    if subtitles.suffix.lower() == ".ass":
        return 1.0
    return LIBASS_DEFAULT_PLAY_HEIGHT / video_height


def force_style(style: SubtitleStyle, scale: float, outline: float) -> str:
    fields = {
        "FontName": style.font_family,
        "FontSize": f"{style.font_size * scale:.1f}",
        "PrimaryColour": ass_color(style.primary_color),
        "SecondaryColour": ass_color(style.highlight_color),
        "OutlineColour": ass_color(style.outline_color),
        "BorderStyle": "1",
        "Outline": f"{outline * scale:.2f}",
        "Shadow": "0",
        "Alignment": "2",
        "MarginV": str(round(style.margin_bottom * scale)),
    }
    return ",".join(f"{key}={value}" for key, value in fields.items())


def subtitle_filter(
    subtitles: Path, style: SubtitleStyle, video_height: int, outline: float, fonts_dir: str
) -> str:
    styled = force_style(style, style_scale(subtitles, video_height), outline)
    rendered = f"subtitles=filename={filter_path(subtitles)}:force_style='{styled}'"
    if fonts_dir:
        rendered += f":fontsdir={filter_path(Path(fonts_dir))}"
    return rendered
