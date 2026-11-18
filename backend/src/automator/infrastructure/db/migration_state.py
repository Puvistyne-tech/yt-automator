from __future__ import annotations

import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

from alembic.script import ScriptDirectory

from automator.infrastructure.db.database import MIGRATIONS_DIR
from automator.shared.errors import describe_error

MISSING_TABLE = "no such table"


@dataclass(frozen=True)
class MigrationState:
    revision: str | None
    head: str | None
    known: bool = True
    error: str = ""


def stored_revision(path: Path) -> str | None:
    if not path.is_file():
        return None
    with closing(sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)) as connection:
        try:
            row = connection.execute("SELECT version_num FROM alembic_version").fetchone()
        except sqlite3.OperationalError as failure:
            if MISSING_TABLE in str(failure):
                return None
            raise
    return str(row[0]) if row else None


def migration_state(path: Path) -> MigrationState:
    scripts = ScriptDirectory(str(MIGRATIONS_DIR))
    head = scripts.get_current_head()
    try:
        revision = stored_revision(path)
    except sqlite3.DatabaseError as failure:
        return MigrationState(None, head, error=describe_error(failure))
    known = revision is None or revision in {script.revision for script in scripts.walk_revisions()}
    return MigrationState(revision, head, known)
