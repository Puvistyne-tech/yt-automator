from __future__ import annotations

from dataclasses import dataclass

from autotube.application.template_lookup import TemplateLookup
from autotube.domain.ports import Clock, IdGenerator
from autotube.domain.template_inputs import TemplateInput, input_errors, new_template
from autotube.domain.template_rules import ensure_creatable
from autotube.domain.template_views import TemplateSummary
from autotube.shared.errors import raise_if_invalid


@dataclass(frozen=True)
class CreateTemplate:
    lookup: TemplateLookup
    ids: IdGenerator
    clock: Clock

    def execute(self, data: TemplateInput) -> TemplateSummary:
        raise_if_invalid(input_errors(data))
        template = new_template(data, self.ids.new(), self.clock.now())
        raise_if_invalid(self.lookup.problems(template))
        ensure_creatable(template, self.lookup.taken_type_ids())
        self.lookup.templates.add(template)
        return self.lookup.present(template)
