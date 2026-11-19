from __future__ import annotations

from collections.abc import Collection
from datetime import datetime

from autotube.domain.pipeline_templates import PipelineTemplate
from autotube.shared.errors import RuleConflict, raise_if_invalid

NAME_MAX_LENGTH = 80
IMMUTABLE_FIELDS = ("audience", "type_id")


def name_errors(name: str) -> dict[str, str]:
    if not name.strip():
        return {"name": "name is required"}
    if len(name) > NAME_MAX_LENGTH:
        return {"name": f"name must be at most {NAME_MAX_LENGTH} characters"}
    return {}


def ensure_editable(template: PipelineTemplate) -> None:
    if template.is_builtin:
        raise RuleConflict(
            "template_builtin",
            f"template {template.name!r} is built in and read-only; duplicate it to customise",
        )


def immutable_errors(current: PipelineTemplate, proposed: PipelineTemplate) -> dict[str, str]:
    return {
        field: f"{field} cannot change after creation; duplicate the template instead"
        for field in IMMUTABLE_FIELDS
        if getattr(current, field) != getattr(proposed, field)
    }


def ensure_type_id_free(type_id: str, taken: Collection[str]) -> None:
    if type_id in taken:
        raise RuleConflict("template_type_taken", f"pipeline type {type_id!r} already exists")


def servable(template: PipelineTemplate, reserved_type_ids: Collection[str]) -> bool:
    return template.is_ready and template.type_id not in reserved_type_ids


def revised(
    current: PipelineTemplate, proposed: PipelineTemplate, now: datetime
) -> PipelineTemplate:
    ensure_editable(current)
    raise_if_invalid(immutable_errors(current, proposed) | name_errors(proposed.name))
    kept = {
        "id": current.id,
        "engine": current.engine,
        "origin": current.origin,
        "created_at": current.created_at,
    }
    return proposed.model_copy(update=kept | {"revision": current.revision + 1, "updated_at": now})
