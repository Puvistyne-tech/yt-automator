import { HttpResponse } from "msw";
import { ruleConflict, validationFailed } from "@/api/mocks/db";
import type { MockState } from "@/api/mocks/fixtures/seed";
import { CANNED_IDEAS, type CannedIdea } from "@/api/mocks/fixtures/suggestions";
import {
  SUGGESTION_COUNT_DEFAULT,
  type SuggestionBody,
  suggestionRequestErrors,
} from "@/api/mocks/suggestionRules";
import { readyWriter } from "@/api/mocks/templatePreview";
import { missingEngineErrors } from "@/api/mocks/templateRules";
import { SUGGESTIONS_UNAVAILABLE } from "@/api/templateErrors";
import type {
  SuggestionRequest,
  TemplateSuggestion,
  TemplateSuggestions,
  TrendOrigin,
} from "@/api/types";

export const NO_TEXT_MODEL = "Connect a text model under Providers to get suggestions.";
export const NO_TRENDS = "No trending videos fit this audience. Try another region or category.";
export const NOTHING_USABLE =
  "None of the suggested ideas passed the checks. Try again, or pick another region or category.";
export const TEXT_MODEL_UNAVAILABLE =
  "The text model is not available right now. Check the text model under Providers and try again.";

function trendOrigin(state: MockState): TrendOrigin {
  return state.channels.some((channel) => channel.status === "connected") ? "youtube" : "sample";
}

function isPlaceholder(state: MockState, providerId: string): boolean {
  return state.descriptors.some((d) => d.provider_id === providerId && d.placeholder);
}

function suggestionOf(idea: CannedIdea, request: SuggestionRequest): TemplateSuggestion {
  return {
    name: idea.name,
    description: idea.description,
    reason: idea.reason,
    based_on: idea.based_on,
    input: {
      engine: request.engine,
      name: idea.name,
      description: idea.description,
      audience: request.audience,
      status: "draft",
      origin: "suggested",
      definition: structuredClone(idea.definition),
    },
  };
}

function suggestions(
  state: MockState,
  request: SuggestionRequest,
  provider: string,
): TemplateSuggestions {
  const asked = CANNED_IDEAS[request.audience].slice(0, request.count ?? SUGGESTION_COUNT_DEFAULT);
  const kept = asked.filter((idea) => idea.failsChecks !== true);
  return {
    suggestions: kept.map((idea) => suggestionOf(idea, request)),
    source: trendOrigin(state),
    dropped: asked.length - kept.length,
    provider,
  };
}

export function suggestionsReply(state: MockState, body: SuggestionBody): Response {
  const errors = suggestionRequestErrors(body);
  if (Object.keys(errors).length > 0) {
    return validationFailed(errors);
  }
  const request = body as unknown as SuggestionRequest;
  if (!state.engines.some((engine) => engine.engine_id === request.engine)) {
    return validationFailed(missingEngineErrors(request.engine));
  }
  if (state.suggestionOutcome === "no_trends") {
    return ruleConflict(SUGGESTIONS_UNAVAILABLE, NO_TRENDS);
  }
  const provider = readyWriter(state);
  if (provider === null) {
    return ruleConflict(SUGGESTIONS_UNAVAILABLE, TEXT_MODEL_UNAVAILABLE);
  }
  if (isPlaceholder(state, provider)) {
    return ruleConflict(SUGGESTIONS_UNAVAILABLE, NO_TEXT_MODEL);
  }
  if (state.suggestionOutcome === "nothing_usable") {
    return ruleConflict(SUGGESTIONS_UNAVAILABLE, NOTHING_USABLE);
  }
  return HttpResponse.json(suggestions(state, request, provider));
}
