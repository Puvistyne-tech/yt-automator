from __future__ import annotations

import re
from pathlib import Path

import pytest

from tests.unit.test_no_channel_branding import (
    REPOSITORY,
    SKIPPED_FOLDERS,
    readable_text,
    tracked_files,
)

RETIRED_APP_NAME = "auto" + "mator"
RETIRED_NAME_PATTERN = re.compile(rf"(?<!yt-){RETIRED_APP_NAME}", re.IGNORECASE)


def mentions_retired_app_name(text: str) -> bool:
    return RETIRED_NAME_PATTERN.search(text) is not None


def carries_retired_app_name(path: Path, root: Path) -> bool:
    relative = path.relative_to(root).as_posix()
    return mentions_retired_app_name(relative) or mentions_retired_app_name(readable_text(path))


def project_files(repository: Path) -> list[Path]:
    return [
        path
        for path in tracked_files(repository)
        if not SKIPPED_FOLDERS.intersection(path.parts) and path.is_file()
    ]


def test_the_repository_uses_only_the_current_app_name() -> None:
    files = project_files(REPOSITORY)
    assert REPOSITORY / "justfile" in files
    found = [
        str(p.relative_to(REPOSITORY)) for p in files if carries_retired_app_name(p, REPOSITORY)
    ]
    assert found == []


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Welcome to YouTube " + RETIRED_APP_NAME.title(), True),
        (RETIRED_APP_NAME.upper() + "_DATA_DIR=./data", True),
        ("python -m " + RETIRED_APP_NAME + ".doctor", True),
        ("git clone https://github.com/Puvistyne-tech/yt-" + RETIRED_APP_NAME + ".git", False),
        ("AUTOTUBE_DATA_DIR and the automations page", False),
    ],
    ids=["display-name", "env-prefix", "module-path", "repository-url", "current-name"],
)
def test_the_scan_flags_the_old_name_and_prefix_but_not_the_repository_url(
    text: str, expected: bool
) -> None:
    assert mentions_retired_app_name(text) is expected


def test_the_scan_checks_file_names_too(tmp_path: Path) -> None:
    path = tmp_path / f"{RETIRED_APP_NAME}_notes" / "plain.txt"
    path.parent.mkdir()
    path.write_text("nothing here", encoding="utf-8")
    assert carries_retired_app_name(path, tmp_path) is True
