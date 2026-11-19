from __future__ import annotations

from autotube.api.container import TemplateUseCases
from autotube.application.create_template import CreateTemplate
from autotube.application.delete_template import DeleteTemplate
from autotube.application.duplicate_template import DuplicateTemplate
from autotube.application.get_template import GetTemplate
from autotube.application.list_template_engines import ListTemplateEngines
from autotube.application.list_templates import ListTemplates
from autotube.application.template_lookup import TemplateLookup
from autotube.application.update_template import UpdateTemplate
from autotube.composition.ports import Ports


def template_use_cases(p: Ports) -> TemplateUseCases:
    lookup = TemplateLookup(p.engines, p.templates, p.automations, p.runs, p.pipelines)
    return TemplateUseCases(
        list_engines=ListTemplateEngines(p.engines),
        list_templates=ListTemplates(lookup),
        get=GetTemplate(lookup),
        create=CreateTemplate(lookup, p.ids, p.clock),
        update=UpdateTemplate(lookup, p.clock),
        delete=DeleteTemplate(lookup),
        duplicate=DuplicateTemplate(lookup, p.ids, p.clock),
    )
