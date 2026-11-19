from __future__ import annotations

from collections.abc import Collection, Iterable
from datetime import datetime

from autotube.domain.automations import Automation
from autotube.domain.pipeline_templates import PipelineTemplate, TemplateOrigin
from autotube.domain.runs import Run
from autotube.domain.template_usage import ensure_unused
from autotube.shared.errors import RuleConflict

NAME_MAX_LENGTH = 80
IMMUTABLE_FIELDS = ("audience", "engine", "type_id")
DRAFT_REMEDY = "it must stay ready until they move to another pipeline and their runs finish"


def name_errors(name: str) -> dict[str, str]:
    trimmed = name.strip()
    if not trimmed:
        return {"name": "name is required"}
    if len(trimmed) > NAME_MAX_LENGTH:
        return {"name": f"name must be at most {NAME_MAX_LENGTH} characters"}
    return {}


def ensure_editable(template: PipelineTemplate) -> None:
    if template.is_builtin:
        raise RuleConflict(
            "template_builtin",
            f"template {template.name!r} is built in and read-only; duplicate it to customise",
        )


def immutable_message(field: str) -> str:
    return f"{field} cannot change after creation; duplicate the template instead"


def immutable_errors(current: PipelineTemplate, proposed: PipelineTemplate) -> dict[str, str]:
    return {
        field: immutable_message(field)
        for field in IMMUTABLE_FIELDS
        if getattr(current, field) != getattr(proposed, field)
    }


def revision_errors(current: PipelineTemplate, proposed: PipelineTemplate) -> dict[str, str]:
    return immutable_errors(current, proposed) | name_errors(proposed.name)


def missing_engine_errors(engine_id: str) -> dict[str, str]:
    return {"engine": f"engine {engine_id!r} is not installed"}


def origin_errors(origin: TemplateOrigin) -> dict[str, str]:
    if origin is TemplateOrigin.BUILTIN:
        return {"origin": "built-in templates come only from installed engines"}
    return {}


def ensure_draft_allowed(
    current: PipelineTemplate,
    proposed: PipelineTemplate,
    automations: Iterable[Automation],
    runs: Iterable[Run],
) -> None:
    if current.is_ready and not proposed.is_ready:
        ensure_unused(current.type_id, automations, runs, DRAFT_REMEDY)


def found_template(
    template_id: str, builtins: Iterable[PipelineTemplate], stored: PipelineTemplate | None
) -> PipelineTemplate | None:
    return next((t for t in builtins if t.id == template_id), stored)


def taken_type_ids(served: Iterable[str], builtins: Iterable[PipelineTemplate]) -> set[str]:
    return {*served, *(template.type_id for template in builtins)}


def ensure_type_id_free(type_id: str, taken: Collection[str]) -> None:
    if type_id in taken:
        raise RuleConflict("template_type_taken", f"pipeline type {type_id!r} already exists")


def ensure_type_id_owned(template: PipelineTemplate, holder_id: str | None) -> None:
    if holder_id is not None and holder_id != template.id:
        ensure_type_id_free(template.type_id, {template.type_id})


def ensure_new_id(template_id: str, taken: bool) -> None:
    if taken:
        raise RuleConflict("template_exists", f"template {template_id!r} already exists")


def servable(template: PipelineTemplate, reserved_type_ids: Collection[str]) -> bool:
    return template.is_ready and template.type_id not in reserved_type_ids


def revised(
    current: PipelineTemplate, proposed: PipelineTemplate, now: datetime
) -> PipelineTemplate:
    kept = {"id": current.id, "origin": current.origin, "created_at": current.created_at}
    return proposed.model_copy(update=kept | {"revision": current.revision + 1, "updated_at": now})
