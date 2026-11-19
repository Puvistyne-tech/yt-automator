from __future__ import annotations

from dataclasses import dataclass

from autotube.application.template_lookup import TemplateLookup
from autotube.domain.ports import Clock, ProviderCatalog, ProviderConfigRepository
from autotube.domain.sample_scripts import (
    SampleScript,
    SampleUnavailableError,
    TemplatePreviewInput,
    preview_template,
    sample_language,
    sample_language_errors,
)
from autotube.domain.template_inputs import input_errors
from autotube.shared.errors import RuleConflict, raise_if_invalid

PREVIEW_UNAVAILABLE = "preview_unavailable"


@dataclass(frozen=True)
class PreviewTemplateScript:
    lookup: TemplateLookup
    catalog: ProviderCatalog
    provider_configs: ProviderConfigRepository
    clock: Clock

    def execute(self, data: TemplatePreviewInput) -> SampleScript:
        raise_if_invalid(input_errors(data))
        template = preview_template(data, self.clock.now())
        engine = self.lookup.valid_engine(template)
        offered = engine.pipeline(template).descriptor.languages
        language = sample_language(data.language, offered)
        raise_if_invalid(sample_language_errors(language, offered))
        providers = self.catalog.resolver(self.provider_configs.list())
        try:
            return engine.sample_script(template, language, data.topic, providers)
        except SampleUnavailableError as error:
            raise RuleConflict(PREVIEW_UNAVAILABLE, str(error)) from error
