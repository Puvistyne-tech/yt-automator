from __future__ import annotations

import re
import unicodedata

SENTENCE_END = re.compile(r"[.!?।]+")
WHITESPACE = re.compile(r"\s+")


def is_punctuation(character: str) -> bool:
    return unicodedata.category(character)[0] in {"P", "S"}


def strip_punctuation(token: str) -> str:
    start, end = 0, len(token)
    while start < end and is_punctuation(token[start]):
        start += 1
    while end > start and is_punctuation(token[end - 1]):
        end -= 1
    return token[start:end]


def words_of(text: str) -> list[str]:
    return [word for token in text.split() if (word := strip_punctuation(token))]


def word_count(text: str) -> int:
    return len(words_of(text))


def sentences_of(text: str) -> list[str]:
    return [part.strip() for part in SENTENCE_END.split(text) if words_of(part)]


def comparable(text: str) -> str:
    return " ".join(word.casefold() for word in words_of(text))


def contains_phrase(text: str, phrase: str) -> bool:
    wanted = comparable(phrase)
    return bool(wanted) and f" {wanted} " in f" {comparable(text)} "


def ends_sentence(word: str) -> bool:
    return bool(SENTENCE_END.search(word[-1:])) if word else False


def collapse_spaces(text: str) -> str:
    return WHITESPACE.sub(" ", text).strip()
