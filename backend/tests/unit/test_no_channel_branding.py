from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPOSITORY = Path(__file__).resolve().parents[3]
SCANNED_TREES = (
    "backend/src",
    "backend/tests",
    "web/src",
    "web/tests",
    "docs",
    "scripts",
    ".claude",
)
RETIRED_NAMES = ("k" + "utty", "குட்டி" + " " + "கதை")
SKIPPED_FOLDERS = frozenset(
    {"__pycache__", "node_modules", ".venv", "dist", ".mypy_cache", ".pytest_cache", ".ruff_cache"}
)


def tracked_files(repository: Path) -> list[Path]:
    listed = subprocess.run(
        ["git", "ls-files", "-z"], cwd=repository, capture_output=True, check=True
    ).stdout
    return [repository / name for name in listed.decode("utf-8").split("\0") if name]


def in_scope(relative: Path) -> bool:
    text = relative.as_posix()
    at_root = len(relative.parts) == 1 and relative.suffix == ".md"
    return at_root or any(text.startswith(f"{tree}/") for tree in SCANNED_TREES)


def scanned_files(repository: Path) -> list[Path]:
    return [
        path
        for path in tracked_files(repository)
        if in_scope(path.relative_to(repository))
        and not SKIPPED_FOLDERS.intersection(path.parts)
        and path.is_file()
    ]


def mentions_retired_name(text: str) -> bool:
    folded = text.casefold()
    return any(name in folded for name in RETIRED_NAMES)


def readable_text(path: Path) -> str:
    content = path.read_bytes()
    return "" if b"\0" in content else content.decode("utf-8", errors="replace")


def branded(path: Path, root: Path) -> bool:
    relative = path.relative_to(root).as_posix()
    return mentions_retired_name(relative) or mentions_retired_name(readable_text(path))


def test_the_repository_carries_no_channel_specific_name() -> None:
    files = scanned_files(REPOSITORY)
    assert {Path("README.md"), Path("CLAUDE.md")} <= {p.relative_to(REPOSITORY) for p in files}
    assert any(path.suffix == ".tsx" for path in files)
    assert [str(path.relative_to(REPOSITORY)) for path in files if branded(path, REPOSITORY)] == []


@pytest.mark.parametrize(
    ("relative", "content", "expected"),
    [
        ("notes.txt", f"Welcome to {RETIRED_NAMES[0].upper()} tales", True),
        ("notes.txt", f"வணக்கம் {RETIRED_NAMES[1]}கள்", True),
        ("notes.txt", "ஒரு குட்டி யானை", False),
        (f"{RETIRED_NAMES[0]}_folder/plain.txt", "nothing here", True),
        (f"art/{RETIRED_NAMES[0].title()}.png", "plain", True),
        ("bytes.bin", b"\xff\xfe\x00 binary " + RETIRED_NAMES[0].encode(), False),
        ("broken.txt", b"\xff\xfe broken utf-8 then plain words", False),
        ("broken.txt", b"\xff " + RETIRED_NAMES[0].encode(), True),
    ],
)
def test_the_scan_checks_names_and_text_and_skips_binary_files(
    tmp_path: Path, relative: str, content: str | bytes, expected: bool
) -> None:
    path = tmp_path / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    data = content.encode("utf-8") if isinstance(content, str) else content
    path.write_bytes(data)
    assert branded(path, tmp_path) is expected


@pytest.mark.parametrize(
    ("relative", "expected"),
    [
        ("README.md", True),
        ("docs/spec/platform.md", True),
        (".claude/rules/architecture.md", True),
        ("web/tests/setup.ts", True),
        ("backend/pyproject.toml", False),
        ("docs", False),
        ("notes/README.md", False),
    ],
)
def test_the_scope_covers_sources_tests_docs_and_root_markdown(
    relative: str, expected: bool
) -> None:
    assert in_scope(Path(relative)) is expected


def test_tracked_files_skip_caches(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    for name in ("docs/a.md", "docs/__pycache__/a.md", "other/b.md"):
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text("text", encoding="utf-8")
    subprocess.run(["git", "add", "-f", "."], cwd=tmp_path, check=True)
    assert [p.relative_to(tmp_path).as_posix() for p in scanned_files(tmp_path)] == ["docs/a.md"]
