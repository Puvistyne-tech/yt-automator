from __future__ import annotations

import os
import shutil
from pathlib import Path


def nearest_existing(path: Path) -> Path:
    return next(candidate for candidate in (path, *path.parents) if candidate.exists())


def disk_usage(path: Path) -> tuple[int, int] | None:
    try:
        usage = shutil.disk_usage(nearest_existing(path))
    except OSError:
        return None
    return usage.total, usage.free


def free_space(path: Path) -> int | None:
    usage = disk_usage(path)
    return usage[1] if usage is not None else None


def file_bytes(path: Path) -> int:
    try:
        return path.lstat().st_size
    except OSError:
        return 0


def tree_bytes(path: Path) -> int:
    if path.is_symlink() or not path.is_dir():
        return file_bytes(path)
    total = 0
    for folder, _, names in os.walk(path):
        total += sum(file_bytes(Path(folder) / name) for name in names)
    return total
