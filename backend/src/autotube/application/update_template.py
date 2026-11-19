from __future__ import annotations

from dataclasses import dataclass

from autotube.application.template_lookup import TemplateLookup
from autotube.domain.pipeline_templates import PipelineTemplate
from autotube.domain.ports import Clock
from autotube.domain.template_inputs import TemplateInput, changed
from autotube.domain.template_rules import (
    engine_change_errors,
    ensure_draft_allowed,
    ensure_editable,
    immutable_errors,
    name_errors,
    revised,
)
from autotube.domain.template_views import TemplateSummary
from autotube.shared.errors import raise_if_invalid


@dataclass(frozen=True)
class UpdateTemplate:
    lookup: TemplateLookup
    clock: Clock

    def execute(self, template_id: str, data: TemplateInput) -> TemplateSummary:
        current = self.lookup.require(template_id)
        ensure_editable(current)
        proposed = changed(current, data)
        raise_if_invalid(self.field_errors(current, proposed, data.engine))
        ensure_draft_allowed(current, proposed, self.lookup.users(current))
        updated = revised(current, proposed, self.clock.now())
        self.lookup.templates.update(updated)
        return self.lookup.present(updated)

    def field_errors(
        self, current: PipelineTemplate, proposed: PipelineTemplate, engine: str
    ) -> dict[str, str]:
        rules = immutable_errors(current, proposed) | engine_change_errors(current, engine)
        return rules | name_errors(proposed.name) | self.lookup.problems(proposed)
