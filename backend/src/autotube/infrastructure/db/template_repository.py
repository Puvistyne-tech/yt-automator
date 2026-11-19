from __future__ import annotations

from pydantic import ValidationError
from sqlmodel import Session, select

from autotube.domain.pipeline_templates import PipelineTemplate
from autotube.domain.template_rules import ensure_new_id, ensure_type_id_owned
from autotube.infrastructure.db.codec import sortable_time, to_payload
from autotube.infrastructure.db.database import Database
from autotube.infrastructure.db.row_repository import RowRepository
from autotube.infrastructure.db.tables import PipelineTemplateRow


def template_row(template: PipelineTemplate) -> PipelineTemplateRow:
    return PipelineTemplateRow(
        id=template.id,
        type_id=template.type_id,
        status=template.status.value,
        created_at=sortable_time(template.created_at),
        payload=to_payload(template),
    )


def type_holder(session: Session, type_id: str) -> PipelineTemplateRow | None:
    statement = select(PipelineTemplateRow).where(PipelineTemplateRow.type_id == type_id)
    return session.exec(statement).first()


def holder_id(session: Session, type_id: str) -> str | None:
    row = type_holder(session, type_id)
    return row.id if row is not None else None


class SqlTemplateRepository(RowRepository[PipelineTemplate, PipelineTemplateRow]):
    def __init__(self, db: Database) -> None:
        super().__init__(db, PipelineTemplateRow, PipelineTemplate, template_row, "created_at")

    def readable(self, row: PipelineTemplateRow | None) -> PipelineTemplate | None:
        if row is None:
            return None
        try:
            return self.decode(row)
        except ValidationError:
            return None

    def list(self) -> list[PipelineTemplate]:
        return [template for row in self.rows() if (template := self.readable(row)) is not None]

    def find_by_type_id(self, type_id: str) -> PipelineTemplate | None:
        with self.db.session() as session:
            return self.readable(type_holder(session, type_id))

    def add(self, template: PipelineTemplate) -> None:
        with self.db.immediate_session() as session:
            ensure_new_id(template.id, session.get(PipelineTemplateRow, template.id) is not None)
            ensure_type_id_owned(template, holder_id(session, template.type_id))
            session.add(self.to_row(template))

    def update(self, template: PipelineTemplate) -> None:
        with self.db.immediate_session() as session:
            ensure_type_id_owned(template, holder_id(session, template.type_id))
            session.merge(self.to_row(template))
