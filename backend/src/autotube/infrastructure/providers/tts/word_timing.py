from __future__ import annotations

from autotube.domain.capabilities import WordTiming


def spoken_words(text: str) -> list[str]:
    return text.split()


def estimate_timings(
    words: list[str], start_seconds: float, end_seconds: float, gap_weight: float = 1.0
) -> tuple[WordTiming, ...]:
    if not words or end_seconds <= start_seconds:
        return ()
    weights = [len(word) + gap_weight for word in words]
    scale = (end_seconds - start_seconds) / sum(weights)
    timings = []
    cursor = start_seconds
    for word, weight in zip(words, weights, strict=True):
        span = weight * scale
        speaking = span * len(word) / weight
        timings.append(
            WordTiming(
                word=word, start_seconds=round(cursor, 3), end_seconds=round(cursor + speaking, 3)
            )
        )
        cursor += span
    return tuple(timings)
