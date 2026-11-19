from __future__ import annotations

from dataclasses import dataclass

from autotube.application.template_lookup import TemplateLookup
from autotube.domain.copy_names import copy_name
from autotube.domain.pipeline_templates import TemplateAudience
from autotube.domain.ports import Clock, IdGenerator
from autotube.domain.template_inputs import duplicated
from autotube.domain.template_rules import (
    NAME_MAX_LENGTH,
    ensure_new_id,
    ensure_type_id_free,
    name_errors,
)
from autotube.domain.template_views import TemplateSummary
from autotube.shared.errors import raise_if_invalid


@dataclass(frozen=True)
class DuplicateTemplate:
    lookup: TemplateLookup
    ids: IdGenerator
    clock: Clock

    def execute(
        self,
        template_id: str,
        name: str | None = None,
        audience: TemplateAudience | None = None,
    ) -> TemplateSummary:
        source = self.lookup.require(template_id)
        chosen = copy_name(source.name, NAME_MAX_LENGTH) if name is None else name
        copy = duplicated(source, self.ids.new(), chosen, audience, self.clock.now())
        raise_if_invalid(name_errors(chosen) | self.lookup.problems(copy))
        ensure_new_id(copy.id, self.lookup.find(copy.id) is not None)
        ensure_type_id_free(copy.type_id, self.lookup.taken_type_ids())
        self.lookup.templates.add(copy)
        return self.lookup.present(copy)
