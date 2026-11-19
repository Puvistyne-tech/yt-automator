from __future__ import annotations

from dataclasses import dataclass, field
from functools import partial

from autotube.application.template_lookup import TemplateLookup
from autotube.application.trend_finder import TrendFinder
from autotube.domain.pipeline_engine import PipelineEngine
from autotube.domain.ports import Clock, ProviderCatalog, ProviderConfigRepository
from autotube.domain.suggestion_screen import screened_suggestions, suggestion_input
from autotube.domain.template_inputs import TemplateInput, input_errors, new_template
from autotube.domain.template_rules import missing_engine_errors
from autotube.domain.template_suggestions import (
    SuggestionBrief,
    SuggestionDrafts,
    SuggestionPolicy,
    SuggestionRequest,
    SuggestionsUnavailableError,
    TemplateSuggestions,
)
from autotube.domain.trends import TrendQuery, audience_trends
from autotube.shared.errors import RuleConflict, ValidationFailed

SUGGESTIONS_UNAVAILABLE = "suggestions_unavailable"
SUGGESTION_TEMPLATE_ID = "suggestion"
NO_TRENDS = "No trending videos fit this audience. Try another region or category."
NOTHING_USABLE = (
    "None of the suggested ideas passed the checks. Try again, or pick another region or category."
)


@dataclass(frozen=True)
class SuggestTemplates:
    lookup: TemplateLookup
    trends: TrendFinder
    catalog: ProviderCatalog
    provider_configs: ProviderConfigRepository
    clock: Clock
    policy: SuggestionPolicy = field(default_factory=SuggestionPolicy)

    def execute(self, request: SuggestionRequest) -> TemplateSuggestions:
        engine = self.engine(request.engine)
        query = TrendQuery(
            region=request.region, category=request.category, limit=self.policy.trend_limit
        )
        report = self.trends.find(query)
        offered = audience_trends(report.videos, request.audience)
        if not offered:
            raise RuleConflict(SUGGESTIONS_UNAVAILABLE, NO_TRENDS)
        brief = SuggestionBrief(audience=request.audience, count=request.count, trends=offered)
        make = partial(suggestion_input, engine.engine_id, request.audience)
        checks = partial(self.problems, engine)
        kept, dropped = screened_suggestions(
            self.drafts(engine, brief), report.videos, make, checks
        )
        if not kept:
            raise RuleConflict(SUGGESTIONS_UNAVAILABLE, NOTHING_USABLE)
        return TemplateSuggestions(suggestions=kept, source=report.origin, dropped=dropped)

    def engine(self, engine_id: str) -> PipelineEngine:
        engine = self.lookup.engines.get(engine_id)
        if engine is None:
            raise ValidationFailed(missing_engine_errors(engine_id))
        return engine

    def drafts(self, engine: PipelineEngine, brief: SuggestionBrief) -> SuggestionDrafts:
        providers = self.catalog.resolver(self.provider_configs.list())
        try:
            return engine.suggested_definitions(brief, providers)
        except SuggestionsUnavailableError as error:
            raise RuleConflict(SUGGESTIONS_UNAVAILABLE, str(error)) from error

    def problems(self, engine: PipelineEngine, data: TemplateInput) -> dict[str, str]:
        errors = input_errors(data)
        if errors:
            return errors
        return engine.problems(new_template(data, SUGGESTION_TEMPLATE_ID, self.clock.now()))
