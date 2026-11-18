from __future__ import annotations

from typing import Any

from sqlmodel import col, select

from automator.domain.ports import RunChange, RunCheck
from automator.domain.runs import Run, RunQuery
from automator.infrastructure.db.codec import sortable_time, to_payload
from automator.infrastructure.db.database import Database
from automator.infrastructure.db.row_repository import RowStore
from automator.infrastructure.db.tables import RunRow


def run_row(run: Run) -> RunRow:
    return RunRow(
        id=run.id,
        automation_id=run.automation_id,
        status=run.status.value,
        trigger=run.trigger.value,
        created_at=sortable_time(run.created_at),
        payload=to_payload(run),
    )


def run_statement(query: RunQuery) -> Any:
    statement = select(RunRow)
    if query.automation_id is not None:
        statement = statement.where(RunRow.automation_id == query.automation_id)
    if query.status is not None:
        statement = statement.where(RunRow.status == query.status.value)
    if query.trigger is not None:
        statement = statement.where(RunRow.trigger == query.trigger.value)
    if query.created_after is not None:
        statement = statement.where(col(RunRow.created_at) >= sortable_time(query.created_after))
    statement = statement.order_by(col(RunRow.created_at).desc(), col(RunRow.id).desc())
    return statement.limit(query.limit) if query.limit is not None else statement


class SqlRunRepository(RowStore[Run, RunRow]):
    def __init__(self, db: Database) -> None:
        super().__init__(db, RunRow, Run, run_row)

    def list(self, query: RunQuery) -> list[Run]:
        with self.db.session() as session:
            rows = session.exec(run_statement(query)).all()
            return [self.decode(row) for row in rows]

    def update(self, run_id: str, change: RunChange) -> Run | None:
        with self.db.immediate_session() as session:
            row = session.get(RunRow, run_id)
            changed = change(self.decode(row)) if row is not None else None
            if changed is not None:
                session.merge(run_row(changed))
            return changed

    def delete_if(self, run_id: str, check: RunCheck) -> Run | None:
        with self.db.immediate_session() as session:
            row = session.get(RunRow, run_id)
            found = self.decode(row) if row is not None else None
            if found is None or not check(found):
                return None
            session.delete(row)
            return found
