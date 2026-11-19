from __future__ import annotations

from autotube.api.container import TemplateUseCases
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
from autotube.composition.ports import Collaborators, Ports


def trend_finder(p: Ports, c: Collaborators) -> TrendFinder:
    return TrendFinder(
        p.channels, p.credentials, c.authorizer, p.youtube, c.quota_report, c.expiry, p.trends
    )


def template_use_cases(p: Ports, c: Collaborators) -> TemplateUseCases:
    lookup = TemplateLookup(p.engines, p.templates, p.automations, p.runs, p.pipelines)
    return TemplateUseCases(
        list_engines=ListTemplateEngines(p.engines),
        list_templates=ListTemplates(lookup),
        get=GetTemplate(lookup),
        create=CreateTemplate(lookup, p.ids, p.clock),
        update=UpdateTemplate(lookup, p.clock),
        delete=DeleteTemplate(lookup),
        duplicate=DuplicateTemplate(lookup, p.ids, p.clock),
        preview=PreviewTemplateScript(lookup, p.catalog, p.provider_configs, p.clock),
        suggest=SuggestTemplates(
            lookup, trend_finder(p, c), p.catalog, p.provider_configs, p.clock
        ),
    )
