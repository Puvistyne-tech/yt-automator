import { HttpResponse } from "msw";
import { ruleConflict, validationFailed } from "@/api/mocks/db";
import { defaultFormat, sampleScript } from "@/api/mocks/fixtures/sampleScripts";
import type { MockState } from "@/api/mocks/fixtures/seed";
import { engineErrors, nameErrors, originErrors } from "@/api/mocks/templateRules";
import type { LanguageOption, TemplatePreviewInput } from "@/api/types";

type Errors = Record<string, string>;

export const TOPIC_MAX_LENGTH = 300;
const TEXT_CAPABILITY = "llm";
export const WRITER_UNAVAILABLE =
  "The script writer is not available right now. Check the text model under Providers and try again.";

export function topicErrors(topic: string): Errors {
  return topic.length > TOPIC_MAX_LENGTH
    ? { topic: `String should have at most ${TOPIC_MAX_LENGTH} characters` }
    : {};
}

export function languageErrors(language: string, offered: readonly LanguageOption[]): Errors {
  const codes = offered.map((option) => option.code);
  return codes.includes(language)
    ? {}
    : { language: `language must be one of: ${codes.join(", ")}` };
}

export function readyWriter(state: MockState): string | null {
  const chain = state.providerConfig.find((config) => config.capability === TEXT_CAPABILITY);
  const ready = chain?.chain.find(
    (choice) =>
      choice.enabled &&
      state.descriptors.some((d) => d.provider_id === choice.provider_id && d.available),
  );
  return ready?.provider_id ?? null;
}

function inputErrors(state: MockState, input: TemplatePreviewInput): Errors {
  return { ...originErrors(input), ...nameErrors(input.name), ...engineErrors(state, input) };
}

function formatOf(state: MockState, input: TemplatePreviewInput): string {
  const chosen = input.definition.structure;
  const engine = state.engines.find((candidate) => candidate.engine_id === input.engine);
  return typeof chosen === "string" ? chosen : engine === undefined ? "" : defaultFormat(engine);
}

function firstFailure(checks: readonly (() => Errors)[]): Errors {
  for (const check of checks) {
    const errors = check();
    if (Object.keys(errors).length > 0) {
      return errors;
    }
  }
  return {};
}

export function previewReply(state: MockState, input: TemplatePreviewInput): Response {
  const offered = state.pipelines[0]?.languages ?? [];
  const language = input.language || (offered[0]?.code ?? "");
  const errors = firstFailure([
    () => topicErrors(input.topic ?? ""),
    () => inputErrors(state, input),
    () => languageErrors(language, offered),
  ]);
  if (Object.keys(errors).length > 0) {
    return validationFailed(errors);
  }
  const provider = readyWriter(state);
  if (provider === null) {
    return ruleConflict("preview_unavailable", WRITER_UNAVAILABLE);
  }
  const format = formatOf(state, input);
  return HttpResponse.json(sampleScript({ format, topic: input.topic ?? "", language, provider }));
}
