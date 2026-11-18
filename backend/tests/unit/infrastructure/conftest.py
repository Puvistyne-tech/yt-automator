from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from automator.infrastructure.db.database import Database


@pytest.fixture
def database(tmp_path: Path) -> Iterator[Database]:
    db = Database(tmp_path / "test.db")
    db.migrate()
    yield db
    db.dispose()
