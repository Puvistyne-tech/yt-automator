from __future__ import annotations

from pathlib import Path

from autotube.shared.errors import UpstreamFailure


def ensure_parent(output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    return output


def require_written(output: Path, what: str) -> Path:
    if not output.is_file() or output.stat().st_size == 0:
        raise UpstreamFailure(f"{what} wrote nothing to {output.name}")
    return output
