from __future__ import annotations

from autotube.domain.pipeline_templates import PipelineTemplate
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


class SqlTemplateRepository(RowRepository[PipelineTemplate, PipelineTemplateRow]):
    def __init__(self, db: Database) -> None:
        super().__init__(db, PipelineTemplateRow, PipelineTemplate, template_row, "created_at")

    def find_by_type_id(self, type_id: str) -> PipelineTemplate | None:
        return self.find_first(PipelineTemplateRow.type_id == type_id)

    def add(self, template: PipelineTemplate) -> None:
        with self.db.immediate_session() as session:
            session.add(self.to_row(template))

    def update(self, template: PipelineTemplate) -> None:
        self.save(template)
