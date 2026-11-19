from __future__ import annotations

import math
from dataclasses import dataclass

from autotube.pipelines.narrated_video.story.model import StoryDraft
from autotube.pipelines.narrated_video.story.words import sentences_of, word_count, words_of
from autotube.pipelines.narrated_video.text.graphemes import grapheme_length

SECONDS_PER_MINUTE = 60.0


@dataclass(frozen=True)
class ReadingMetrics:
    average_sentence_words: float
    long_word_share: float


def narration_of(story: StoryDraft) -> str:
    return " ".join(scene.narration for scene in story.scenes)


def label_sentences(story: StoryDraft) -> list[str]:
    return [f"{text.strip()}." for scene in story.scenes for text in scene.texts if text.strip()]


def reading_text(story: StoryDraft) -> str:
    return " ".join([narration_of(story), *label_sentences(story)])


def total_words(story: StoryDraft) -> int:
    return sum(word_count(scene.narration) for scene in story.scenes)


def reading_metrics(text: str, long_word_graphemes: float) -> ReadingMetrics:
    sentences = sentences_of(text)
    words = words_of(text)
    if not sentences or not words:
        return ReadingMetrics(average_sentence_words=0.0, long_word_share=0.0)
    long_words = [word for word in words if grapheme_length(word) > long_word_graphemes]
    return ReadingMetrics(
        average_sentence_words=len(words) / len(sentences),
        long_word_share=len(long_words) / len(words),
    )


def estimated_seconds(story: StoryDraft, words_per_minute: float) -> float:
    return total_words(story) * SECONDS_PER_MINUTE / max(words_per_minute, 1.0)


def word_range(low_seconds: float, high_seconds: float, words_per_minute: float) -> tuple[int, int]:
    rate = max(words_per_minute, 1.0) / SECONDS_PER_MINUTE
    return math.ceil(max(low_seconds, 0.0) * rate), math.floor(high_seconds * rate)
