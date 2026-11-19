from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from autotube.application.create_template import CreateTemplate
from autotube.application.delete_template import DeleteTemplate
from autotube.application.duplicate_template import DuplicateTemplate
from autotube.application.get_template import GetTemplate
from autotube.application.list_template_engines import ListTemplateEngines
from autotube.application.list_templates import ListTemplates
from autotube.application.template_lookup import TemplateLookup
from autotube.application.update_template import UpdateTemplate
from autotube.domain.automations import Automation
from autotube.domain.pipeline_templates import TemplateAudience, TemplateStatus
from autotube.domain.template_inputs import TemplateInput
from autotube.domain.template_views import TemplateSummary
from tests.fixtures.builders import add_automation
from tests.fixtures.fake_engines import ENGINE_ID, FakeEngineCatalog
from tests.fixtures.fake_repositories import InMemoryTemplates
from tests.fixtures.harness import Harness


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

    @property
    def lookup(self) -> TemplateLookup:
        h = self.harness
        return TemplateLookup(self.engines, self.templates, h.automations, h.pipelines)

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

    def created(self, **changes: Any) -> TemplateSummary:
        return self.create().execute(template_input(**changes))

    def automation_using(self, type_id: str, name: str = "Bedtime") -> Automation:
        made = add_automation(self.harness, name=name)
        using = made.model_copy(update={"pipeline_type": type_id})
        self.harness.automations.save(using)
        return using
