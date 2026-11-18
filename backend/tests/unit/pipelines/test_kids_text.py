from __future__ import annotations

import pytest

from automator.pipelines.kids_story.languages import ordered_languages, primary_language
from automator.pipelines.kids_story.settings.story import StorySettings, ThemeMode
from automator.pipelines.kids_story.story.normalise import speakable, speech_rules
from automator.pipelines.kids_story.story.numbers import number_to_words
from automator.pipelines.kids_story.story.reading import reading_metrics
from automator.pipelines.kids_story.story.themes import choose_theme
from automator.pipelines.kids_story.story.words import (
    comparable,
    contains_phrase,
    sentences_of,
    word_count,
    words_of,
)
from automator.pipelines.kids_story.text.graphemes import (
    grapheme_clusters,
    grapheme_length,
)


def test_words_strip_punctuation_and_keep_tamil_marks() -> None:
    assert words_of('"Hello," said Kutty. "Let\'s go!"') == [
        "Hello",
        "said",
        "Kutty",
        "Let's",
        "go",
    ]
    assert words_of("குட்டி யானை நடந்தான்.") == ["குட்டி", "யானை", "நடந்தான்"]
    assert word_count("  ") == 0


def test_phrases_match_whole_words_only() -> None:
    assert contains_phrase("Sharing, makes everyone HAPPIER!", "sharing makes everyone happier.")
    assert not contains_phrase("He was on a diet.", "die")
    assert comparable("Be kind, be brave!") == "be kind be brave"


def test_sentences_split_on_end_marks() -> None:
    assert sentences_of("One. Two words! Three? ") == ["One", "Two words", "Three"]


@pytest.mark.parametrize(
    ("value", "english"),
    [
        (0, "zero"),
        (7, "seven"),
        (15, "fifteen"),
        (40, "forty"),
        (42, "forty-two"),
        (100, "one hundred"),
        (305, "three hundred and five"),
        (1000, "one thousand"),
        (2024, "two thousand twenty-four"),
        (5_000_000, "5000000"),
    ],
)
def test_english_number_words(value: int, english: str) -> None:
    rules = speech_rules("en")
    assert rules is not None and number_to_words(value, rules.numbers) == english


@pytest.mark.parametrize(
    ("value", "tamil"),
    [
        (3, "மூன்று"),
        (12, "பன்னிரண்டு"),
        (20, "இருபது"),
        (25, "இருபத்து ஐந்து"),
        (100, "நூறு"),
        (105, "நூற்று ஐந்து"),
        (900, "தொள்ளாயிரம்"),
        (1000, "ஆயிரம்"),
        (1500, "ஆயிரத்து ஐநூறு"),
        (3000, "மூன்று ஆயிரம்"),
    ],
)
def test_tamil_number_words(value: int, tamil: str) -> None:
    rules = speech_rules("ta")
    assert rules is not None and number_to_words(value, rules.numbers) == tamil


def test_speakable_english() -> None:
    spoken = speakable("Dr. Owl counted 3 stars & 1,200 fireflies, 50% more!", "en")
    assert spoken == (
        "Doctor Owl counted three stars and one thousand two hundred fireflies, fifty percent more!"
    )


def test_speakable_tamil() -> None:
    assert speakable("குட்டி 2 மாம்பழம் & 10 வாழைப்பழம்.", "ta") == (
        "குட்டி இரண்டு மாம்பழம் மற்றும் பத்து வாழைப்பழம்."
    )


def test_speakable_unknown_language_only_tidies_spaces() -> None:
    assert speakable("  hola   3 ", "es") == "hola 3"


def test_grapheme_clusters_keep_tamil_vowel_signs_and_virama() -> None:
    assert grapheme_clusters("குட்டி") == ["கு", "ட்", "டி"]
    assert grapheme_length("மகிழ்ச்சி") == 5
    assert grapheme_length("kutty") == 5


def test_reading_metrics_use_graphemes() -> None:
    metrics = reading_metrics("Kutty walked. The elephant smiled happily.", 7)
    assert metrics.average_sentence_words == 3.0
    assert metrics.long_word_share == pytest.approx(1 / 6)


def test_theme_rotation_avoids_recent_and_fixed_wins() -> None:
    rotate = StorySettings(themes=["a", "b", "c"], recent_themes=["a", "b"], avoid_repeat_last=2)
    assert choose_theme(rotate, "seed") == "c"
    everything_recent = rotate.model_copy(
        update={"recent_themes": ["a", "b", "c"], "avoid_repeat_last": 3}
    )
    assert choose_theme(everything_recent, "seed") in {"a", "b", "c"}
    fixed = StorySettings(theme_mode=ThemeMode.FIXED, fixed_theme="kindness")
    assert choose_theme(fixed, "seed") == "kindness"


def test_primary_language_falls_back_to_the_first_selected() -> None:
    assert primary_language("en", ("ta",)) == "ta"
    assert primary_language("ta", ("en", "ta")) == "ta"
    assert ordered_languages("ta", ("en", "ta")) == ["ta", "en"]
