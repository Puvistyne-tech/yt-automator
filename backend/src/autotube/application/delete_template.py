from __future__ import annotations

from dataclasses import dataclass

from autotube.application.template_lookup import TemplateLookup
from autotube.domain.deletion_rules import ensure_template_deletable
from autotube.domain.template_rules import ensure_editable


@dataclass(frozen=True)
class DeleteTemplate:
    lookup: TemplateLookup

    def execute(self, template_id: str) -> None:
        template = self.lookup.require(template_id)
        ensure_editable(template)
        ensure_template_deletable(template, self.lookup.automations.list())
        self.lookup.templates.delete(template.id)
