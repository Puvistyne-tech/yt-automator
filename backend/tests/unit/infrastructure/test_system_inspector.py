from __future__ import annotations

import shutil
import sqlite3
import stat
from contextlib import closing
from pathlib import Path

import pytest

from automator.infrastructure.config import RuntimeConfig
from automator.infrastructure.db.database import Database
from automator.infrastructure.db.migration_state import migration_state
from automator.infrastructure.diagnostics.system_inspector import (
    build_system_inspector,
    free_space,
    tool_version,
    writable_dir,
)


def script(folder: Path, body: str) -> Path:
    path = folder / "tool"
    path.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def config_for(tmp_path: Path) -> RuntimeConfig:
    return RuntimeConfig(data_dir=tmp_path / "data", web_dist_dir=tmp_path / "dist")


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ("echo 'ffmpeg version 7.1 Copyright (c) 2000'", "ffmpeg version 7.1"),
        ("exit 3", ""),
        ("sleep 5", ""),
        ("true", ""),
    ],
)
def test_tool_version_reads_the_first_line(tmp_path: Path, body: str, expected: str) -> None:
    assert tool_version(str(script(tmp_path, body)), 0.5) == expected


def test_tool_version_of_a_missing_binary_is_empty(tmp_path: Path) -> None:
    assert tool_version(str(tmp_path / "absent"), 0.5) == ""


def test_writable_dir_walks_up_to_an_existing_folder(tmp_path: Path) -> None:
    assert writable_dir(tmp_path / "a" / "b")
    blocker = tmp_path / "file"
    blocker.write_text("x", encoding="utf-8")
    assert not writable_dir(blocker / "data")


def test_free_space_is_unknown_when_the_disk_cannot_be_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def unreadable(_: Path) -> None:
        raise OSError("no disk")

    monkeypatch.setattr(shutil, "disk_usage", unreadable)
    assert free_space(tmp_path) is None


def test_facts_of_a_fresh_install(tmp_path: Path) -> None:
    facts = build_system_inspector(config_for(tmp_path)).facts()
    assert facts.data_dir == str(tmp_path / "data")
    assert facts.data_dir_writable
    assert facts.free_bytes is not None and facts.free_bytes > 0
    assert facts.database_revision is None
    assert facts.database_head == "0001"
    assert not facts.ui_built
    assert not (tmp_path / "data").exists()


def test_facts_see_the_ui_build(tmp_path: Path) -> None:
    (tmp_path / "dist").mkdir()
    (tmp_path / "dist" / "index.html").write_text("<html></html>", encoding="utf-8")
    assert build_system_inspector(config_for(tmp_path)).facts().ui_built


def test_migrated_database_is_at_head(tmp_path: Path) -> None:
    database = Database(tmp_path / "automator.db", 100)
    database.migrate()
    database.dispose()
    state = migration_state(tmp_path / "automator.db")
    assert (state.revision, state.head, state.known, state.error) == ("0001", "0001", True, "")


def write_sqlite(path: Path, *statements: str) -> Path:
    with closing(sqlite3.connect(path)) as connection:
        for statement in statements:
            connection.execute(statement)
        connection.commit()
    return path


def test_unknown_revision_is_flagged(tmp_path: Path) -> None:
    path = write_sqlite(
        tmp_path / "db.sqlite",
        "CREATE TABLE alembic_version (version_num TEXT)",
        "INSERT INTO alembic_version VALUES ('9999')",
    )
    state = migration_state(path)
    assert (state.revision, state.known) == ("9999", False)


def test_database_without_migrations_has_no_revision(tmp_path: Path) -> None:
    path = write_sqlite(tmp_path / "db.sqlite", "CREATE TABLE other (x INTEGER)")
    assert migration_state(path).revision is None


def test_empty_version_table_has_no_revision(tmp_path: Path) -> None:
    path = write_sqlite(tmp_path / "db.sqlite", "CREATE TABLE alembic_version (version_num TEXT)")
    assert migration_state(path).revision is None


def test_corrupt_database_reports_an_error(tmp_path: Path) -> None:
    path = tmp_path / "db.sqlite"
    path.write_bytes(b"not a database at all, just bytes" * 200)
    assert "not a database" in migration_state(path).error
