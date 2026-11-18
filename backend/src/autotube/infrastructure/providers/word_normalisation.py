from __future__ import annotations

import unicodedata

WORD_CATEGORIES = "LMN"


def normalised(word: str) -> str:
    kept = [char for char in word.casefold() if unicodedata.category(char)[0] in WORD_CATEGORIES]
    return "".join(kept)
