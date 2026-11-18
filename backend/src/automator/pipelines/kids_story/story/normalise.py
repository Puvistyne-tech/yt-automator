from __future__ import annotations

import re
from functools import cache

from pydantic import BaseModel, ConfigDict

from automator.pipelines.kids_story.resources import resource_json, resource_names
from automator.pipelines.kids_story.story.numbers import NumberWords, number_to_words
from automator.pipelines.kids_story.story.words import collapse_spaces

FOLDER = "speech"
DIGITS = re.compile(r"\d{1,3}(?:,\d{3})+|\d+")


class SpeechRules(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    abbreviations: dict[str, str]
    symbols: dict[str, str]
    numbers: NumberWords


@cache
def speech_rules(language: str) -> SpeechRules | None:
    if f"{language}.json" not in resource_names(FOLDER, ".json"):
        return None
    return SpeechRules.model_validate(resource_json(FOLDER, f"{language}.json"))


def whole_token(key: str) -> re.Pattern[str]:
    return re.compile(rf"(?<!\w){re.escape(key)}(?!\w)")


def expand_abbreviations(text: str, rules: SpeechRules) -> str:
    for key in sorted(rules.abbreviations, key=len, reverse=True):
        text = whole_token(key).sub(rules.abbreviations[key], text)
    return text


def expand_symbols(text: str, rules: SpeechRules) -> str:
    for symbol, spoken in rules.symbols.items():
        text = text.replace(symbol, f" {spoken} ")
    return text


def expand_numbers(text: str, rules: SpeechRules) -> str:
    def spoken(match: re.Match[str]) -> str:
        return f" {number_to_words(int(match.group(0).replace(',', '')), rules.numbers)} "

    return DIGITS.sub(spoken, text)


def speakable(text: str, language: str) -> str:
    rules = speech_rules(language)
    if rules is None:
        return collapse_spaces(text)
    expanded = expand_numbers(expand_symbols(expand_abbreviations(text, rules), rules), rules)
    return re.sub(r"\s+([,.!?;:])", r"\1", collapse_spaces(expanded))
