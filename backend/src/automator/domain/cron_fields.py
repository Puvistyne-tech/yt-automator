from __future__ import annotations

from dataclasses import dataclass

MONTH_NAMES = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")
WEEKDAY_NAMES = ("SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT")


class CronSyntaxError(ValueError):
    pass


@dataclass(frozen=True)
class FieldSpec:
    name: str
    low: int
    high: int
    aliases: tuple[str, ...] = ()
    alias_start: int = 0


MINUTE = FieldSpec("minute", 0, 59)
HOUR = FieldSpec("hour", 0, 23)
DAY_OF_MONTH = FieldSpec("day of month", 1, 31)
MONTH = FieldSpec("month", 1, 12, MONTH_NAMES, 1)
DAY_OF_WEEK = FieldSpec("day of week", 0, 7, WEEKDAY_NAMES, 0)


def parse_value(text: str, spec: FieldSpec) -> int:
    upper = text.upper()
    if upper in spec.aliases:
        return spec.aliases.index(upper) + spec.alias_start
    if not text.isdigit():
        raise CronSyntaxError(f"{spec.name}: {text!r} is not a number")
    value = int(text)
    if not spec.low <= value <= spec.high:
        raise CronSyntaxError(f"{spec.name}: {value} is outside {spec.low}-{spec.high}")
    return value


def parse_step(text: str, spec: FieldSpec) -> int:
    if not text.isdigit() or int(text) < 1:
        raise CronSyntaxError(f"{spec.name}: step {text!r} must be a positive number")
    return int(text)


def parse_bounds(text: str, spec: FieldSpec, has_step: bool) -> tuple[int, int]:
    if text == "*":
        return spec.low, spec.high
    start_text, dash, end_text = text.partition("-")
    start = parse_value(start_text, spec)
    if not dash:
        return start, spec.high if has_step else start
    end = parse_value(end_text, spec)
    if end < start:
        raise CronSyntaxError(f"{spec.name}: range {text!r} runs backwards")
    return start, end


def parse_item(text: str, spec: FieldSpec) -> set[int]:
    range_text, slash, step_text = text.partition("/")
    step = parse_step(step_text, spec) if slash else 1
    start, end = parse_bounds(range_text, spec, bool(slash))
    return set(range(start, end + 1, step))


def parse_field(text: str, spec: FieldSpec) -> frozenset[int]:
    if not text:
        raise CronSyntaxError(f"{spec.name}: empty field")
    values: set[int] = set()
    for item in text.split(","):
        if not item:
            raise CronSyntaxError(f"{spec.name}: empty list item")
        values |= parse_item(item, spec)
    return frozenset(values)
