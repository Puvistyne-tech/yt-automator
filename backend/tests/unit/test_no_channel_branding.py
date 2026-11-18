from __future__ import annotations

from pathlib import Path

import pytest

REPOSITORY = Path(__file__).resolve().parents[3]
SOURCE_TREES = ("backend/src", "web/src")
RETIRED_CHANNEL_NAME = "k" + "utty"
SKIPPED_FOLDERS = frozenset({"__pycache__", "node_modules"})


def source_files(tree: Path) -> list[Path]:
    return [
        path
        for path in sorted(tree.rglob("*"))
        if path.is_file() and not SKIPPED_FOLDERS.intersection(path.parts)
    ]


def mentions_retired_name(path: Path) -> bool:
    text = path.read_bytes().decode("utf-8", errors="ignore")
    return RETIRED_CHANNEL_NAME in text.casefold()


@pytest.mark.parametrize("tree", SOURCE_TREES)
def test_source_tree_carries_no_channel_specific_name(tree: str) -> None:
    root = REPOSITORY / tree
    files = source_files(root)
    assert files, tree
    assert [str(path.relative_to(root)) for path in files if mentions_retired_name(path)] == []


def test_the_scan_finds_the_name_in_any_case(tmp_path: Path) -> None:
    sample = tmp_path / "sample.txt"
    sample.write_text(f"Welcome to {RETIRED_CHANNEL_NAME.upper()} tales", encoding="utf-8")
    assert mentions_retired_name(sample)
    assert source_files(tmp_path) == [sample]
