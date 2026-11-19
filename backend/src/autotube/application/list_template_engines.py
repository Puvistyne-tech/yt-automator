from __future__ import annotations

from dataclasses import dataclass

from autotube.domain.ports import EngineCatalog
from autotube.domain.template_views import EngineSummary, engine_summary


@dataclass(frozen=True)
class ListTemplateEngines:
    engines: EngineCatalog

    def execute(self) -> list[EngineSummary]:
        return [engine_summary(engine) for engine in self.engines.list()]
