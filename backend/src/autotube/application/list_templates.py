from __future__ import annotations

from dataclasses import dataclass

from autotube.application.template_lookup import TemplateLookup
from autotube.domain.template_views import TemplateSummary


@dataclass(frozen=True)
class ListTemplates:
    lookup: TemplateLookup

    def execute(self) -> list[TemplateSummary]:
        return self.lookup.present_all(self.lookup.everything())
