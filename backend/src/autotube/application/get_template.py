from __future__ import annotations

from dataclasses import dataclass

from autotube.application.template_lookup import TemplateLookup
from autotube.domain.template_views import TemplateSummary


@dataclass(frozen=True)
class GetTemplate:
    lookup: TemplateLookup

    def execute(self, template_id: str) -> TemplateSummary:
        return self.lookup.present(self.lookup.require(template_id))
