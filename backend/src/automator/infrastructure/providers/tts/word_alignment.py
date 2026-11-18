from __future__ import annotations

import difflib
import unicodedata

from automator.domain.capabilities import WordTiming
from automator.infrastructure.providers.tts.word_timing import estimate_timings


def normalised(word: str) -> str:
    kept = [char for char in word.casefold() if unicodedata.category(char)[0] in "LMN"]
    return "".join(kept)


def matched_times(
    words: list[str], recognised: list[WordTiming]
) -> tuple[dict[int, WordTiming], float]:
    matcher = difflib.SequenceMatcher(
        a=[normalised(word) for word in words],
        b=[normalised(timing.word) for timing in recognised],
        autojunk=False,
    )
    found: dict[int, WordTiming] = {}
    for block in matcher.get_matching_blocks():
        for offset in range(block.size):
            heard = recognised[block.b + offset]
            found[block.a + offset] = heard.model_copy(update={"word": words[block.a + offset]})
    return found, len(found) / len(words)


def fill_gap(
    words: list[str], first: int, last: int, start: float, end: float
) -> tuple[WordTiming, ...]:
    return estimate_timings(words[first:last], start, max(end, start + 0.01 * (last - first)))


def align_words(
    words: list[str], recognised: list[WordTiming], duration: float, min_match: float
) -> tuple[WordTiming, ...] | None:
    if not words or not recognised:
        return None
    found, ratio = matched_times(words, recognised)
    if ratio < min_match:
        return None
    result: list[WordTiming] = []
    index = 0
    while index < len(words):
        if index in found:
            result.append(found[index])
            index += 1
            continue
        stop = next((later for later in range(index, len(words)) if later in found), len(words))
        start = result[-1].end_seconds if result else 0.0
        end = found[stop].start_seconds if stop in found else duration
        result.extend(fill_gap(words, index, stop, start, end))
        index = stop
    return tuple(result)
