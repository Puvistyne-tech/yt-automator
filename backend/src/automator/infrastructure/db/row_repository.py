from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel
from sqlmodel import SQLModel, col, select

from automator.infrastructure.db.codec import from_payload
from automator.infrastructure.db.database import Database


class RowStore[M: BaseModel, R: SQLModel]:
    def __init__(
        self, db: Database, row_type: type[R], model_type: type[M], to_row: Callable[[M], R]
    ) -> None:
        self.db = db
        self.row_type = row_type
        self.model_type = model_type
        self.to_row = to_row

    def decode(self, row: R) -> M:
        payload: dict[str, Any] = row.model_dump()["payload"]
        return from_payload(self.model_type, payload)

    def get(self, row_id: str) -> M | None:
        with self.db.session() as session:
            row = session.get(self.row_type, row_id)
            return self.decode(row) if row is not None else None

    def save(self, model: M) -> None:
        with self.db.immediate_session() as session:
            session.merge(self.to_row(model))

    def delete(self, row_id: str) -> None:
        with self.db.immediate_session() as session:
            row = session.get(self.row_type, row_id)
            if row is not None:
                session.delete(row)


class RowRepository[M: BaseModel, R: SQLModel](RowStore[M, R]):
    def __init__(
        self,
        db: Database,
        row_type: type[R],
        model_type: type[M],
        to_row: Callable[[M], R],
        order_column: str,
    ) -> None:
        super().__init__(db, row_type, model_type, to_row)
        self.order_column = order_column

    def list(self) -> list[M]:
        order = col(getattr(self.row_type, self.order_column))
        with self.db.session() as session:
            rows = session.exec(select(self.row_type).order_by(order)).all()
            return [self.decode(row) for row in rows]
