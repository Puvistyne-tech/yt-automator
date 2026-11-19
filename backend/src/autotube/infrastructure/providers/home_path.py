from __future__ import annotations

from pathlib import Path


def home_expanded(path: str) -> str:
    return str(Path(path).expanduser())
