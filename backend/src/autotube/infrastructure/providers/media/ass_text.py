from __future__ import annotations

from collections.abc import Sequence

from autotube.shared.errors import UpstreamFailure

TEXT_REPLACEMENTS = (("\\", "/"), ("{", "("), ("}", ")"), ("\r", " "), ("\n", " "))
HEX_DIGITS = "0123456789abcdefABCDEF"
OPAQUE = 1.0
FULL_ALPHA = 255


def ass_bgr(hex_color: str) -> str:
    digits = hex_color.lstrip("#")
    if len(digits) != 6 or any(char not in HEX_DIGITS for char in digits):
        raise UpstreamFailure(f"subtitle colour {hex_color!r} is not #RRGGBB")
    red, green, blue = digits[0:2], digits[2:4], digits[4:6]
    return f"{blue}{green}{red}".upper()


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
