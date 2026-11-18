from __future__ import annotations

from pathlib import Path

import pytest

from automator.domain.capabilities import WordTiming
from automator.pipelines.kids_story.art import lettering
from automator.pipelines.kids_story.settings.root import KidsStorySettings
from automator.pipelines.kids_story.settings.subtitles import SubtitleSettings
from automator.pipelines.kids_story.subtitles.layout import subtitle_layout
from automator.pipelines.kids_story.subtitles.subtitle_font import subtitle_font
from automator.pipelines.kids_story.subtitles.timeline_cues import cue_rules
from automator.pipelines.kids_story.subtitles.timing import segment_cues
from tests.fixtures.fonts import embedded_font, embedded_font_family
from tests.fixtures.kids_data import quick_settings

NARRATION = {
    "en": "Kavin the little elephant lifted his long trunk high into the warm morning air and "
    "reached for the biggest, sweetest, most wonderfully golden mango on the whole tree.",
    "ta": "கவின் தன் தும்பிக்கையை உயர்த்தி, மிகப் பெரிய, மிக இனிப்பான மாம்பழத்தைப் பறித்தான். "
    "மிட்டு கிளி மகிழ்ச்சியுடன் பாட்டுப் பாடியது, சின்னு அணில் கைதட்டிச் சிரித்தது.",
}
VARIANTS = ("episode", "short")
ESTIMATE = SubtitleSettings().letter_width_estimate


def timed(text: str) -> list[WordTiming]:
    return [
        WordTiming(word=word, start_seconds=index * 0.2, end_seconds=index * 0.2 + 0.15)
        for index, word in enumerate(text.split())
    ]


def settings_with(files: list[str]) -> KidsStorySettings:
    return quick_settings(subtitles={"font_files": {"en": files, "ta": files}})


@pytest.mark.parametrize("language", sorted(NARRATION))
@pytest.mark.parametrize("variant", VARIANTS)
@pytest.mark.parametrize("measured", [True, False])
@pytest.mark.usefixtures("shaping")
def test_cues_stay_within_their_lines_the_usable_width_and_the_narration(
    language: str, variant: str, measured: bool, tmp_path: Path
) -> None:
    settings = settings_with([str(embedded_font(tmp_path))] if measured else [])
    layout = subtitle_layout(settings, language, variant)
    rules = cue_rules(settings.subtitles, layout)
    cues = segment_cues(timed(NARRATION[language]), 0.0, 60.0, rules)
    assert (layout.font.file is not None) is measured
    assert " ".join(cue.text for cue in cues) == NARRATION[language]
    for cue in cues:
        assert 1 <= len(cue.lines) <= layout.max_lines
        assert all(layout.font.measure(line) <= layout.line_width for line in cue.lines)
    assert all(left.end <= right.start for left, right in zip(cues, cues[1:], strict=False))


def test_layout_reserves_the_side_margins() -> None:
    layout = subtitle_layout(quick_settings(), "ta", "short")
    assert (layout.width, layout.side_margin, layout.line_width) == (720, 29, 662)


def test_estimated_widths_grow_with_letters_and_language() -> None:
    settings = settings_with(["/nowhere/a.ttf", "/nowhere/b.ttf"])
    english = subtitle_font(settings.subtitles, "en", 50)
    tamil = subtitle_font(settings.subtitles, "ta", 50)
    assert english.measure("abcd") == pytest.approx(4 * 50 * ESTIMATE.en)
    assert tamil.measure("சின்னு") == pytest.approx(3 * 50 * ESTIMATE.ta)
    assert (english.family, tamil.family, english.file) == ("Noto Sans", "Noto Sans Tamil", None)


def test_unreadable_font_files_are_skipped_in_order(tmp_path: Path) -> None:
    broken = tmp_path / "broken.ttf"
    broken.write_bytes(b"not a font")
    font = subtitle_font(settings_with([str(broken)]).subtitles, "en", 40)
    assert font.file is None and font.measure("ab") == pytest.approx(2 * 40 * ESTIMATE.en)
    good = embedded_font(tmp_path)
    files = [str(tmp_path / "missing.ttf"), str(broken), str(good)]
    found = subtitle_font(settings_with(files).subtitles, "en", 40)
    assert (found.file, found.family) == (good, embedded_font_family())


def test_tamil_without_shaping_keeps_the_file_but_measures_by_estimate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(lettering, "shaping_available", lambda: False)
    file = embedded_font(tmp_path)
    settings = settings_with([str(file)])
    tamil = subtitle_font(settings.subtitles, "ta", 40)
    assert (tamil.file, tamil.family) == (file, embedded_font_family())
    assert tamil.measure("சின்னு") == pytest.approx(3 * 40 * ESTIMATE.ta)
    english = subtitle_font(settings.subtitles, "en", 40)
    assert english.file == file and english.measure("ab") != pytest.approx(2 * 40 * ESTIMATE.en)


class OddlyNamedFont:
    def getname(self) -> tuple[str, str]:
        return ("Fonts & Co.", "Regular")


def test_an_unsafe_family_name_is_measured_and_drawn_like_a_missing_font(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    found = (Path("/fonts/odd.ttf"), OddlyNamedFont())
    monkeypatch.setattr(lettering, "load_font", lambda *_: found)
    font = subtitle_font(SubtitleSettings(), "en", 40)
    assert (font.family, font.file) == ("Noto Sans", None)
    assert font.measure("ab") == pytest.approx(2 * 40 * ESTIMATE.en)
