from __future__ import annotations

from dataclasses import dataclass

from autotube.application.lookups import require
from autotube.application.template_lookup import TemplateLookup
from autotube.domain.deletion_rules import ensure_template_deletable
from autotube.domain.template_rules import ensure_editable


@dataclass(frozen=True)
class DeleteTemplate:
    lookup: TemplateLookup

    def execute(self, template_id: str) -> None:
        type_id = self.deletable_type_id(template_id)
        ensure_template_deletable(type_id, self.lookup.all_automations(), self.lookup.all_runs())
        self.lookup.templates.delete(template_id)

    def deletable_type_id(self, template_id: str) -> str:
        template = self.lookup.find(template_id)
        if template is None:
            stored = self.lookup.templates.type_id_of(template_id)
            return require(stored, "template", template_id)
        ensure_editable(template)
        return template.type_id
