from __future__ import annotations

import pytest

from autotube.domain.srt import parse_srt

TIMING = "00:00:01,000 --> 00:00:02,500"


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ("", []),
        ("garbage", []),
        (f"1\n{TIMING}\nHello,\nfriends\n", [(1.0, 2.5, ("Hello,", "friends"))]),
        (f"{TIMING}\nகுட்டி\nயானை", [(1.0, 2.5, ("குட்டி", "யானை"))]),
        (f"1\n{TIMING}\n", [(1.0, 2.5, ())]),
        (
            f"1\r\n{TIMING}\r\nHi\r\n\r\n2\r\n{TIMING}\r\nYo\r\n",
            [
                (1.0, 2.5, ("Hi",)),
                (1.0, 2.5, ("Yo",)),
            ],
        ),
        (f"\ufeff1\n{TIMING}\nHi\n", [(1.0, 2.5, ("Hi",))]),
        (
            f"1\n{TIMING}\nA\n\nnot a cue\n\n2\n{TIMING}\nB\n",
            [
                (1.0, 2.5, ("A",)),
                (1.0, 2.5, ("B",)),
            ],
        ),
        ("1\n00:00:01.000 --> 00:00:02.000\nDots\n", []),
        ("1\n0:00:01,000 --> 0:00:02,000\nShort\n", []),
        ("1\n00:99:99,999 --> 01:00:00,000\nLenient\n", [(6039.999, 3600.0, ("Lenient",))]),
    ],
)
def test_srt_blocks_parse_into_timed_lines(
    content: str, expected: list[tuple[float, float, tuple[str, ...]]]
) -> None:
    parsed = [(entry.start, entry.end, entry.lines) for entry in parse_srt(content)]
    assert parsed == expected


def test_an_entry_reads_as_one_line_of_text() -> None:
    [entry] = parse_srt(f"{TIMING}\nHello,\nfriends")
    assert entry.text == "Hello, friends"
