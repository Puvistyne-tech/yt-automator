from __future__ import annotations

from dataclasses import dataclass

from automator.pipelines.kids_story.story.model import StoryDraft
from automator.pipelines.kids_story.story.words import sentences_of, word_count, words_of
from automator.pipelines.kids_story.subtitles.graphemes import grapheme_length


@dataclass(frozen=True)
class ReadingMetrics:
    average_sentence_words: float
    long_word_share: float


def narration_of(story: StoryDraft) -> str:
    return " ".join(scene.narration for scene in story.scenes)


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
    return total_words(story) * 60.0 / max(words_per_minute, 1.0)
