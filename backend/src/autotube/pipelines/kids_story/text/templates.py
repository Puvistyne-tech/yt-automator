from __future__ import annotations

import re
from collections.abc import Mapping

PLACEHOLDER = re.compile(r"\{([a-z_]+)\}")


def render_template(template: str, values: Mapping[str, str]) -> str:
    return PLACEHOLDER.sub(lambda match: values.get(match.group(1), match.group(0)), template)


def unknown_placeholders(template: str, known: frozenset[str]) -> list[str]:
    return sorted(set(PLACEHOLDER.findall(template)) - known)
