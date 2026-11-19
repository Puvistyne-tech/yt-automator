from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from autotube.application.create_template import CreateTemplate
from autotube.application.delete_template import DeleteTemplate
from autotube.application.duplicate_template import DuplicateTemplate
from autotube.application.get_template import GetTemplate
from autotube.application.list_template_engines import ListTemplateEngines
from autotube.application.list_templates import ListTemplates
from autotube.application.preview_template_script import PreviewTemplateScript
from autotube.application.suggest_templates import SuggestTemplates
from autotube.application.template_lookup import TemplateLookup
from autotube.application.trend_finder import TrendFinder
from autotube.application.update_template import UpdateTemplate
from autotube.domain.automations import Automation
from autotube.domain.pipeline_templates import TemplateAudience, TemplateStatus
from autotube.domain.run_enums import RunStatus
from autotube.domain.runs import Run
from autotube.domain.template_inputs import TemplateInput
from autotube.domain.template_views import TemplateSummary
from tests.fixtures.builders import add_automation, started_run
from tests.fixtures.fake_engines import ENGINE_ID, FakeEngineCatalog
from tests.fixtures.fake_repositories import InMemoryTemplates
from tests.fixtures.harness import Harness
from tests.fixtures.suggestion_data import StaticTrends


def template_input(**changes: Any) -> TemplateInput:
    fields: dict[str, Any] = {
        "engine": ENGINE_ID,
        "name": "Space facts",
        "description": "Short facts about space",
        "audience": TemplateAudience.GENERAL,
        "status": TemplateStatus.READY,
        "definition": {"brief": "planets"},
    }
    return TemplateInput.model_validate(fields | changes)


@dataclass
class TemplateRig:
    harness: Harness
    templates: InMemoryTemplates = field(default_factory=InMemoryTemplates)
    engines: FakeEngineCatalog = field(default_factory=FakeEngineCatalog)
    trends: StaticTrends = field(default_factory=StaticTrends)

    @property
    def lookup(self) -> TemplateLookup:
        h = self.harness
        return TemplateLookup(self.engines, self.templates, h.automations, h.runs, h.pipelines)

    def list_engines(self) -> ListTemplateEngines:
        return ListTemplateEngines(self.engines)

    def list_templates(self) -> ListTemplates:
        return ListTemplates(self.lookup)

    def get(self) -> GetTemplate:
        return GetTemplate(self.lookup)

    def create(self) -> CreateTemplate:
        return CreateTemplate(self.lookup, self.harness.ids, self.harness.clock)

    def update(self) -> UpdateTemplate:
        return UpdateTemplate(self.lookup, self.harness.clock)

    def delete(self) -> DeleteTemplate:
        return DeleteTemplate(self.lookup)

    def duplicate(self) -> DuplicateTemplate:
        return DuplicateTemplate(self.lookup, self.harness.ids, self.harness.clock)

    def preview(self) -> PreviewTemplateScript:
        h = self.harness
        return PreviewTemplateScript(self.lookup, h.catalog, h.provider_configs, h.clock)

    def suggest(self) -> SuggestTemplates:
        h = self.harness
        finder = TrendFinder(
            h.channels,
            h.credentials,
            h.authorizer,
            h.youtube,
            h.quota_report,
            h.expiry,
            self.trends,
        )
        return SuggestTemplates(self.lookup, finder, h.catalog, h.provider_configs, h.clock)

    def created(self, **changes: Any) -> TemplateSummary:
        return self.create().execute(template_input(**changes))

    def automation_using(self, type_id: str, name: str = "Bedtime") -> Automation:
        made = add_automation(self.harness, name=name)
        using = made.model_copy(update={"pipeline_type": type_id})
        self.harness.automations.save(using)
        return using

    def run_using(self, type_id: str, status: RunStatus) -> Run:
        started = started_run(self.harness, name="Runner")
        stored = started.model_copy(update={"pipeline_type": type_id, "status": status})
        self.harness.runs.save(stored)
        self.harness.automations.delete(started.automation_id)
        return stored
