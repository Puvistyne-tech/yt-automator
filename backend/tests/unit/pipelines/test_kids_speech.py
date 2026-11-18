from __future__ import annotations

from typing import Any

import pytest

from autotube.pipelines.kids_story.settings.base import LocalizedText
from autotube.pipelines.kids_story.stages.voice import filled_line, lines_to_speak, voice_for
from autotube.pipelines.kids_story.story.normalise import (
    SpeechRules,
    expand_abbreviations,
    speakable,
    speech_rules,
)
from autotube.pipelines.kids_story.story.numbers import number_to_words
from tests.fixtures.kids_data import quick_settings, story

SCENES = [f"scene-{index}" for index in range(9)]


@pytest.mark.parametrize(
    ("sections", "changes", "segments"),
    [
        ({}, {}, ["intro", *SCENES, "outro", "hook"]),
        ({"voice": {"include_intro": False, "include_outro": False}}, {}, [*SCENES, "hook"]),
        ({"series": {"intro_line": {"en": "  ", "ta": ""}}}, {}, [*SCENES, "outro", "hook"]),
        ({"short": {"hook_line": False}}, {}, ["intro", *SCENES, "outro"]),
        ({"short": {"enabled": False}}, {}, ["intro", *SCENES, "outro"]),
        ({}, {"hook_line": ""}, ["intro", *SCENES, "outro"]),
    ],
)
def test_lines_to_speak_follow_settings(
    sections: dict[str, Any], changes: dict[str, Any], segments: list[str]
) -> None:
    lines = lines_to_speak(story(**changes), quick_settings(**sections))
    assert [line.segment for line in lines] == segments


@pytest.mark.parametrize(
    ("series", "language", "intro"),
    [
        ({}, "en", "Hello, little friends! Welcome to Story Time. Let's begin!"),
        (
            {"name": {"en": "Bedtime tales", "ta": "இரவுக் கதைகள்"}},
            "ta",
            "வணக்கம், சின்ன நண்பர்களே! இரவுக் கதைகள் உங்களை அன்புடன் வரவேற்கிறது. கதையைத் தொடங்குவோம்!",
        ),
        (
            {"intro_line": {"en": "Hi from {series} and {nope}", "ta": ""}},
            "en",
            "Hi from Story Time and {nope}",
        ),
        (
            {"name": {"en": "A {series} {title} B", "ta": "x"}, "intro_line": {"en": "{series}!"}},
            "en",
            "A {series} {title} B!",
        ),
        ({"intro_line": {"en": "{title} by {series}", "ta": ""}}, "en", None),
    ],
)
def test_intro_line_fills_in_the_series_name(
    series: dict[str, Any], language: str, intro: str | None
) -> None:
    told = story(language)
    lines = lines_to_speak(told, quick_settings(series=series))
    assert lines[0].segment == "intro"
    assert lines[0].text == (intro or f"{told.title} by Story Time")


def test_outro_line_fills_in_the_series_name() -> None:
    settings = quick_settings(series={"outro_line": {"en": "Bye from {series}!", "ta": ""}})
    assert lines_to_speak(story(), settings)[-2].text == "Bye from Story Time!"


def test_a_language_without_its_own_line_falls_back_to_english() -> None:
    line = LocalizedText(en="Welcome to {series}", ta="")
    assert filled_line(line, {"series": "Tales"}, "fr") == "Welcome to Tales"


def test_voice_for_prefers_a_character_override_then_the_narrator() -> None:
    cast = [member.model_dump() for member in quick_settings().cast]
    cast[1]["voice_override"] = {"en": "parrot", "ta": ""}
    settings = quick_settings(voice={"narrator_voice": {"en": "story_en", "ta": "story_ta"}})
    settings = settings.model_validate({**settings.model_dump(), "cast": cast})
    assert voice_for(settings, "mittu", "en") == "parrot"
    assert voice_for(settings, "mittu", "ta") == "story_ta"
    assert voice_for(settings, "dragon", "en") == "story_en"
    assert voice_for(settings, "narrator", "ta") == "story_ta"


@pytest.mark.parametrize(
    ("text", "language", "spoken"),
    [
        ("", "en", ""),
        ("   ", "ta", ""),
        ("50%.", "en", "fifty percent."),
        ("Drive to St. Mary", "en", "Drive to Saint Mary"),
        ("டாக்டர். ஆமை 5 கி.மீ. நடந்தார்", "ta", "டாக்டர் ஆமை ஐந்து கிலோமீட்டர் நடந்தார்"),
        ("10% + 2", "ta", "பத்து சதவீதம் கூட்டல் இரண்டு"),
    ],
)
def test_speakable_edge_cases(text: str, language: str, spoken: str) -> None:
    assert speakable(text, language) == spoken


def test_longer_abbreviations_are_expanded_first() -> None:
    rules = speech_rules("en")
    assert rules is not None
    custom = SpeechRules(
        abbreviations={"g.": "gee", "e.g.": "for example"},
        symbols={},
        numbers=rules.numbers,
    )
    assert expand_abbreviations("toys, e.g. balls", custom) == "toys, for example balls"


@pytest.mark.parametrize(
    ("language", "value", "words"),
    [
        ("en", 999_999, "nine hundred and ninety-nine thousand nine hundred and ninety-nine"),
        ("en", 1_000_000, "1000000"),
        ("en", -3, "-3"),
        ("en", 21_000, "twenty-one thousand"),
        ("ta", 0, "பூஜ்ஜியம்"),
        (
            "ta",
            999_999,
            "தொள்ளாயிரத்து தொண்ணூற்று ஒன்பது ஆயிரத்து தொள்ளாயிரத்து தொண்ணூற்று ஒன்பது",
        ),
        ("ta", 1_000_000, "1000000"),
    ],
)
def test_number_word_boundaries(language: str, value: int, words: str) -> None:
    rules = speech_rules(language)
    assert rules is not None and number_to_words(value, rules.numbers) == words
