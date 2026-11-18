from __future__ import annotations

from collections.abc import Sequence

from automator.domain.capabilities import SubtitleStyle
from automator.domain.srt import SrtEntry
from automator.shared.errors import UpstreamFailure

FONT_NAME_EXTRAS = frozenset(" -_")
NO_WRAPPING = 2
SMART_WRAPPING = 0
TEXT_REPLACEMENTS = (("\\", "/"), ("{", "("), ("}", ")"))
STYLE_FORMAT = (
    "Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
    "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, "
    "Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding"
)
EVENT_FORMAT = "Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"


def ass_color(hex_color: str) -> str:
    digits = hex_color.lstrip("#")
    if len(digits) != 6 or any(char not in "0123456789abcdefABCDEF" for char in digits):
        raise UpstreamFailure(f"subtitle colour {hex_color!r} is not #RRGGBB")
    red, green, blue = digits[0:2], digits[2:4], digits[4:6]
    return f"&H00{blue}{green}{red}".upper()


def font_name(family: str) -> str:
    if family and all(char.isalnum() or char in FONT_NAME_EXTRAS for char in family):
        return family
    raise UpstreamFailure(
        f"subtitle font {family!r} may only use letters, digits, spaces, '-' and '_'"
    )


def ass_time(seconds: float) -> str:
    centis = round(max(seconds, 0.0) * 100)
    hours, rest = divmod(centis, 360_000)
    minutes, rest = divmod(rest, 6_000)
    whole, centis = divmod(rest, 100)
    return f"{hours}:{minutes:02d}:{whole:02d}.{centis:02d}"


def ass_line(line: str) -> str:
    for unsafe, safe in TEXT_REPLACEMENTS:
        line = line.replace(unsafe, safe)
    return line


def ass_text(lines: Sequence[str]) -> str:
    return "\\N".join(ass_line(line) for line in lines)


def style_line(style: SubtitleStyle, outline: float) -> str:
    fields = [
        "Default",
        font_name(style.font_family),
        str(style.font_size),
        ass_color(style.primary_color),
        ass_color(style.highlight_color),
        ass_color(style.outline_color),
        "&H00000000",
        *("0", "0", "0", "0", "100", "100", "0", "0", "1"),
        f"{outline:g}",
        "0",
        "2",
        *(str(style.margin_sides),) * 2,
        str(style.margin_bottom),
        "1",
    ]
    return "Style: " + ",".join(fields)


def ass_document(
    entries: Sequence[SrtEntry], style: SubtitleStyle, size: tuple[int, int], outline: float
) -> str:
    width, height = size
    header = [
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {width}",
        f"PlayResY: {height}",
        f"WrapStyle: {SMART_WRAPPING if style.wrap_lines else NO_WRAPPING}",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        f"Format: {STYLE_FORMAT}",
        style_line(style, outline),
        "",
        "[Events]",
        f"Format: {EVENT_FORMAT}",
    ]
    events = [
        f"Dialogue: 0,{ass_time(entry.start)},{ass_time(entry.end)},Default,,0,0,0,,"
        + ass_text(entry.lines)
        for entry in entries
    ]
    return "\n".join([*header, *events]) + "\n"
