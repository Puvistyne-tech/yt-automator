from __future__ import annotations

from collections.abc import Sequence

LANGUAGE_NAMES = {"en": "English", "ta": "Tamil"}


def language_name(code: str) -> str:
    return LANGUAGE_NAMES.get(code, code)


def primary_language(preferred: str, languages: Sequence[str]) -> str:
    if preferred in languages or not languages:
        return preferred
    return languages[0]


def ordered_languages(primary: str, languages: Sequence[str]) -> list[str]:
    return [primary, *(code for code in languages if code != primary)]
