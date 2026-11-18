from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import date

from automator.domain.runs import RunQuery
from automator.infrastructure.db.database import Database
from automator.infrastructure.db.run_repository import SqlRunRepository
from automator.infrastructure.db.settings_repositories import SqlQuotaLedger
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
