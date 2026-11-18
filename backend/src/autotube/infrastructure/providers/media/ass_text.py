from __future__ import annotations

import re
from collections.abc import Sequence

from autotube.domain.image_style import HEX_COLOUR_PATTERN, rgb_of_hex
from autotube.shared.errors import UpstreamFailure

TEXT_REPLACEMENTS = (("\\", "/"), ("{", "("), ("}", ")"), ("\r", " "), ("\n", " "))
OPAQUE = 1.0
FULL_ALPHA = 255


def ass_bgr(hex_color: str) -> str:
    if re.fullmatch(HEX_COLOUR_PATTERN, hex_color) is None:
        raise UpstreamFailure(f"subtitle colour {hex_color!r} is not #RRGGBB")
    red, green, blue = rgb_of_hex(hex_color)
    return f"{blue:02X}{green:02X}{red:02X}"


def ass_color(hex_color: str, opacity: float = OPAQUE) -> str:
    alpha = round((1.0 - opacity) * FULL_ALPHA)
    return f"&H{alpha:02X}{ass_bgr(hex_color)}"


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
