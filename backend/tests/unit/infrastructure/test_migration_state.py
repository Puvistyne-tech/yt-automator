from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from autotube.infrastructure.db.database import Database
from autotube.infrastructure.db.migration_state import migration_state
from tests.fixtures.fake_diagnostics import MIGRATION_HEAD as HEAD


def write_sqlite(path: Path, *statements: str) -> Path:
    with closing(sqlite3.connect(path)) as connection:
        for statement in statements:
            connection.execute(statement)
        connection.commit()
    return path


def test_migrated_database_is_at_head(tmp_path: Path) -> None:
    database = Database(tmp_path / "autotube.db", 100)
    database.migrate()
    database.dispose()
    state = migration_state(tmp_path / "autotube.db")
    assert (state.revision, state.head, state.known, state.error) == (HEAD, HEAD, True, "")


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


def test_unexpected_version_table_reports_an_error(tmp_path: Path) -> None:
    path = write_sqlite(tmp_path / "db.sqlite", "CREATE TABLE alembic_version (other TEXT)")
    state = migration_state(path)
    assert "no such column" in state.error
    assert state.revision is None


def test_corrupt_database_reports_an_error(tmp_path: Path) -> None:
    path = tmp_path / "db.sqlite"
    path.write_bytes(b"not a database at all, just bytes" * 200)
    assert "not a database" in migration_state(path).error
