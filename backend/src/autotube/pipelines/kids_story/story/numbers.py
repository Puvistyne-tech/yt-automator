from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

HUNDRED = 100
THOUSAND = 1000
LARGEST = 999_999
TEENS_END = 20


class NumberWords(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    units: list[str] = Field(min_length=20, max_length=20)
    tens: list[str] = Field(min_length=10, max_length=10)
    tens_prefix: list[str] = Field(min_length=10, max_length=10)
    tens_joiner: str
    hundreds: list[str] = Field(min_length=10, max_length=10)
    hundreds_prefix: list[str] = Field(min_length=10, max_length=10)
    thousand: str
    thousand_prefix: str
    one_thousand: str
    one_thousand_prefix: str


def below_hundred(value: int, words: NumberWords) -> str:
    if value < TEENS_END:
        return words.units[value]
    tens, rest = divmod(value, 10)
    if rest == 0:
        return words.tens[tens]
    return f"{words.tens_prefix[tens]}{words.tens_joiner}{words.units[rest]}"


def below_thousand(value: int, words: NumberWords) -> str:
    if value < HUNDRED:
        return below_hundred(value, words)
    hundreds, rest = divmod(value, HUNDRED)
    if rest == 0:
        return words.hundreds[hundreds]
    return f"{words.hundreds_prefix[hundreds]} {below_hundred(rest, words)}"


def thousands_head(count: int, words: NumberWords, has_rest: bool) -> str:
    if count == 1:
        return words.one_thousand_prefix if has_rest else words.one_thousand
    suffix = words.thousand_prefix if has_rest else words.thousand
    return f"{below_thousand(count, words)} {suffix}"


def number_to_words(value: int, words: NumberWords) -> str:
    if value < 0 or value > LARGEST:
        return str(value)
    if value < THOUSAND:
        return below_thousand(value, words)
    count, rest = divmod(value, THOUSAND)
    head = thousands_head(count, words, rest > 0)
    return f"{head} {below_thousand(rest, words)}" if rest else head
