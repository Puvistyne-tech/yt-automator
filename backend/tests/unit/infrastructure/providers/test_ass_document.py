from __future__ import annotations

from pathlib import Path

import pytest

from autotube.domain.capabilities import SubtitleStyle
from autotube.domain.srt import SrtEntry
from autotube.infrastructure.providers.media.ass_document import ass_document, ass_text, ass_time
from autotube.infrastructure.providers.media.ass_subtitles import with_ass_subtitles
from autotube.shared.errors import UpstreamFailure
from tests.unit.infrastructure.providers.media_fixtures import composition

STYLE = SubtitleStyle(
    burn_in=True, font_family="Noto Sans Tamil", font_size=64, margin_bottom=280, margin_sides=29
)
ENTRIES = [
    SrtEntry(start=0.5, end=2.25, lines=("குட்டி தன்", "தும்பிக்கையை")),
    SrtEntry(start=3661.0, end=3662.004, lines=("a {b} c\\d",)),
]


def test_document_draws_lines_as_given_at_frame_pixels() -> None:
    document = ass_document(ENTRIES, STYLE, (720, 1280), 3.0)
    assert "PlayResX: 720\nPlayResY: 1280\nWrapStyle: 2\n" in document
    assert (
        "Style: Default,Noto Sans Tamil,64,&H00FFFFFF,&H004AD5FF,&H00000000,&H00000000,"
        "0,0,0,0,100,100,0,0,1,3,0,2,29,29,280,1\n"
    ) in document
    assert "Dialogue: 0,0:00:00.50,0:00:02.25,Default,,0,0,0,,குட்டி தன்\\Nதும்பிக்கையை" in document
    assert document.endswith("Dialogue: 0,1:01:01.00,1:01:02.00,Default,,0,0,0,,a (b) c/d\n")


def test_wrapping_can_be_left_to_the_renderer() -> None:
    style = STYLE.model_copy(update={"wrap_lines": True})
    assert "WrapStyle: 0" in ass_document([], style, (1280, 720), 0.0)


def test_times_are_centiseconds() -> None:
    assert (ass_time(-1.0), ass_time(59.999), ass_time(7322.5)) == (
        "0:00:00.00",
        "0:01:00.00",
        "2:02:02.50",
    )


@pytest.mark.parametrize(
    ("line", "drawn"),
    [
        ("a {b} c", "a (b) c"),
        ("back\\slash", "back/slash"),
        ("not \\N a break", "not /N a break"),
        ("one\ntwo", "one two"),
        ("one\r\ntwo", "one  two"),
        ("commas, stay", "commas, stay"),
        ("", ""),
    ],
)
def test_text_cannot_carry_override_tags_or_breaks(line: str, drawn: str) -> None:
    assert ass_text([line]) == drawn


def test_outline_and_safe_font_names_are_kept() -> None:
    style = STYLE.model_copy(update={"font_family": "Noto Sans Tamil-Bold_2"})
    assert ",Noto Sans Tamil-Bold_2,64," in ass_document([], style, (10, 10), 2.5)
    assert ",1,2.5,0,2," in ass_document([], style, (10, 10), 2.5)


@pytest.mark.parametrize("family", ["Kid's Font", "Comic Sans, MS", "A:B", "", "x[y]"])
def test_unsafe_font_names_are_refused(family: str) -> None:
    with pytest.raises(UpstreamFailure, match="may only use letters, digits"):
        ass_document([], STYLE.model_copy(update={"font_family": family}), (10, 10), 0.0)


def test_srt_subtitles_become_an_ass_file_beside_the_video(tmp_path: Path) -> None:
    srt = tmp_path / "en.srt"
    srt.write_text("1\n00:00:01,000 --> 00:00:02,000\nHello,\nfriends\n", encoding="utf-8")
    burned = with_ass_subtitles(composition(subtitles=srt), (320, 180), tmp_path / "v.mp4", 2.0)
    assert burned.subtitles == tmp_path / "v.ass"
    assert "0:00:01.00,0:00:02.00,Default,,0,0,0,,Hello,\\Nfriends" in burned.subtitles.read_text(
        encoding="utf-8"
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"subtitles": None},
        {"subtitles": Path("/w/authored.ass")},
        {"subtitles": Path("/w/authored.ASS")},
        {"subtitle_style": SubtitleStyle(burn_in=False)},
    ],
)
def test_other_subtitles_are_left_alone(changes: dict[str, object], tmp_path: Path) -> None:
    original = composition(**changes)
    assert with_ass_subtitles(original, (320, 180), tmp_path / "v.mp4", 2.0) == original
    assert not (tmp_path / "v.ass").exists()


def test_an_empty_srt_becomes_an_ass_file_without_dialogue(tmp_path: Path) -> None:
    srt = tmp_path / "empty.srt"
    srt.write_text("garbage", encoding="utf-8")
    burned = with_ass_subtitles(composition(subtitles=srt), (320, 180), tmp_path / "v.mp4", 2.0)
    assert burned.subtitles is not None
    document = burned.subtitles.read_text(encoding="utf-8")
    assert "[Events]" in document and "Dialogue:" not in document
