from __future__ import annotations

from dataclasses import dataclass

from autotube.application.template_lookup import TemplateLookup
from autotube.domain.pipeline_templates import TemplateAudience
from autotube.domain.ports import Clock, IdGenerator
from autotube.domain.template_inputs import duplicated
from autotube.domain.template_rules import copy_name, ensure_creatable, name_errors
from autotube.domain.template_views import TemplateSummary
from autotube.shared.errors import raise_if_invalid


@dataclass(frozen=True)
class DuplicateTemplate:
    lookup: TemplateLookup
    ids: IdGenerator
    clock: Clock
    name_suffix: str = " (copy)"

    def execute(
        self,
        template_id: str,
        name: str | None = None,
        audience: TemplateAudience | None = None,
    ) -> TemplateSummary:
        source = self.lookup.require(template_id)
        chosen = copy_name(source.name, self.name_suffix) if name is None else name
        raise_if_invalid(name_errors(chosen))
        copy = duplicated(source, self.ids.new(), chosen, audience, self.clock.now())
        raise_if_invalid(self.lookup.problems(copy))
        ensure_creatable(copy, self.lookup.taken_type_ids())
        self.lookup.templates.add(copy)
        return self.lookup.present(copy)
