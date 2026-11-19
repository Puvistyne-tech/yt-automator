from __future__ import annotations

import re
from collections.abc import Mapping

EMPTY = ""
PLACEHOLDER = re.compile(r"\{([a-z_]+)\}")


def render_template(template: str, values: Mapping[str, str], missing: str | None = None) -> str:
    def value(match: re.Match[str]) -> str:
        fallback = match.group(0) if missing is None else missing
        return values.get(match.group(1), fallback)

    return PLACEHOLDER.sub(value, template)


def unknown_placeholders(template: str, known: frozenset[str]) -> list[str]:
    return sorted(set(PLACEHOLDER.findall(template)) - known)
