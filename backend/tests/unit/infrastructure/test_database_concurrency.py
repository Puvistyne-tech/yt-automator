from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from functools import partial
from pathlib import Path

import pytest
from sqlalchemy import text

from automator.domain.run_parts import RunLog
from automator.domain.runs import Run, RunQuery
from automator.infrastructure.db.database import Database
from automator.infrastructure.db.run_repository import SqlRunRepository
from automator.infrastructure.db.settings_repositories import SqlQuotaLedger
from tests.fixtures.fake_runtime import START
from tests.unit.infrastructure.records import run

WORKERS = 8
WRITES = 15
DAY = date(2026, 1, 5)


def write_batch(database: Database, worker: int) -> None:
    runs, ledger = SqlRunRepository(database), SqlQuotaLedger(database)
    for index in range(WRITES):
        runs.save(run(f"w{worker}-{index}", index))
        ledger.record("cred-1", 1, DAY)


def test_threads_share_the_database_safely(database: Database) -> None:
    with ThreadPoolExecutor(WORKERS) as pool:
        list(pool.map(lambda worker: write_batch(database, worker), range(WORKERS)))
    assert len(SqlRunRepository(database).list(RunQuery())) == WORKERS * WRITES
    assert SqlQuotaLedger(database).used_today("cred-1", DAY) == WORKERS * WRITES


def with_log(entry: RunLog, stored: Run) -> Run:
    return stored.model_copy(update={"logs": (*stored.logs, entry)})


def append_log(database: Database, worker: int) -> None:
    runs = SqlRunRepository(database)
    for index in range(WRITES):
        entry = RunLog(at=START, message=f"{worker}-{index}")
        runs.update("shared", partial(with_log, entry))


def test_updates_never_lose_a_concurrent_change(database: Database) -> None:
    SqlRunRepository(database).save(run("shared"))
    with ThreadPoolExecutor(WORKERS) as pool:
        list(pool.map(lambda worker: append_log(database, worker), range(WORKERS)))
    stored = SqlRunRepository(database).get("shared")
    assert stored is not None and len(stored.logs) == WORKERS * WRITES


def test_update_skips_missing_runs_and_declined_changes(database: Database) -> None:
    runs = SqlRunRepository(database)
    assert runs.update("missing", lambda stored: stored) is None
    runs.save(run("kept"))
    assert runs.update("kept", lambda _stored: None) is None
    assert runs.get("kept") == run("kept")


def test_a_failing_change_rolls_back(database: Database) -> None:
    runs = SqlRunRepository(database)
    runs.save(run("kept"))

    def explode(_stored: Run) -> Run:
        raise RuntimeError("no")

    with pytest.raises(RuntimeError):
        runs.update("kept", explode)
    assert runs.update("kept", lambda stored: stored.model_copy(update={"error": "x"}))
    assert runs.get("kept") == run("kept").model_copy(update={"error": "x"})


def test_the_busy_timeout_is_configurable(tmp_path: Path) -> None:
    database = Database(tmp_path / "busy.db", 250)
    with database.engine.connect() as connection:
        assert connection.execute(text("PRAGMA busy_timeout")).scalar() == 250
    database.dispose()


def test_a_save_waits_for_an_open_update_and_succeeds(database: Database) -> None:
    runs = SqlRunRepository(database)
    runs.save(run("held"))
    inside, release, saved = threading.Event(), threading.Event(), threading.Event()

    def hold(stored: Run) -> Run:
        inside.set()
        release.wait(10)
        return stored.model_copy(update={"error": "held"})

    def save_other() -> None:
        runs.save(run("other"))
        saved.set()

    updater = threading.Thread(target=runs.update, args=("held", hold))
    updater.start()
    assert inside.wait(10)
    saver = threading.Thread(target=save_other)
    saver.start()
    assert not saved.wait(0.2)
    release.set()
    updater.join(10)
    saver.join(10)
    assert saved.is_set()
    assert {item.id for item in runs.list(RunQuery())} == {"other", "held"}
    stored = runs.get("held")
    assert stored is not None and stored.error == "held"
