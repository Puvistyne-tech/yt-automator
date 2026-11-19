from __future__ import annotations

from dataclasses import dataclass

from autotube.application.template_lookup import TemplateLookup
from autotube.domain.ports import Clock
from autotube.domain.template_inputs import TemplateInput, changed
from autotube.domain.template_rules import (
    ensure_draft_allowed,
    ensure_editable,
    revised,
    revision_errors,
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
        raise_if_invalid(revision_errors(current, proposed) | self.lookup.problems(proposed))
        lookup = self.lookup
        ensure_draft_allowed(current, proposed, lookup.all_automations(), lookup.all_runs())
        updated = revised(current, proposed, self.clock.now())
        self.lookup.templates.update(updated)
        return self.lookup.present(updated)
