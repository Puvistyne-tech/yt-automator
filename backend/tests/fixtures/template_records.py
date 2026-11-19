from __future__ import annotations

from typing import Any

from autotube.domain.pipeline_templates import (
    PipelineTemplate,
    TemplateAudience,
    TemplateOrigin,
    TemplateStatus,
    user_type_id,
)
from tests.fixtures.fake_runtime import START


def template(template_id: str = "tpl-1", **changes: Any) -> PipelineTemplate:
    fields: dict[str, Any] = {
        "id": template_id,
        "type_id": user_type_id(template_id),
        "engine": "narrated_video",
        "name": "Fact videos",
        "audience": TemplateAudience.GENERAL,
        "status": TemplateStatus.READY,
        "origin": TemplateOrigin.BLANK,
        "created_at": START,
        "updated_at": START,
    }
    return PipelineTemplate.model_validate(fields | changes)
