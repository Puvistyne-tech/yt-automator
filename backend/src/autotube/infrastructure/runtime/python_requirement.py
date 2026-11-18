from __future__ import annotations

import re
from importlib.metadata import PackageNotFoundError, metadata

LOWER_BOUND = re.compile(r">=\s*(\d+)\.(\d+)")


def minimum_python(spec: str) -> tuple[int, int] | None:
    match = LOWER_BOUND.search(spec)
    return (int(match[1]), int(match[2])) if match else None


def required_python(package: str = "autotube") -> tuple[int, int] | None:
    try:
        spec = metadata(package).get("Requires-Python") or ""
    except PackageNotFoundError:
        return None
    return minimum_python(spec)
