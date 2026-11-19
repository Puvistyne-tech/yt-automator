import { AUDIENCE_LABELS } from "@/api/labels";
import type { Run, TemplateInput } from "@/api/types";
import { isJsonObject } from "@/shared/isJsonObject";

export function runPath(run: Pick<Run, "id">): string {
  return `/runs/${encodeURIComponent(run.id)}`;
}

export function automationPath(id: string): string {
  return `/automations/${encodeURIComponent(id)}`;
}

export const PIPELINE_QUERY = "pipeline";

export function newAutomationPath(typeId: string): string {
  return `/automations/new?${new URLSearchParams({ [PIPELINE_QUERY]: typeId }).toString()}`;
}

export function pipelinePath(templateId: string): string {
  return `/pipelines/${encodeURIComponent(templateId)}`;
}

export const NEW_PIPELINE_PATH = "/pipelines/new";

export interface NewPipelineState {
  prefill: TemplateInput;
}

export function newPipelineState(input: TemplateInput): NewPipelineState {
  return { prefill: input };
}

function isTemplateInput(value: unknown): value is TemplateInput {
  if (!isJsonObject(value)) {
    return false;
  }
  const texts = [value.engine, value.name, value.description];
  const audience =
    typeof value.audience === "string" && Object.hasOwn(AUDIENCE_LABELS, value.audience);
  return (
    texts.every((text) => typeof text === "string") && audience && isJsonObject(value.definition)
  );
}

export function prefilledInputOf(state: unknown): TemplateInput | null {
  const prefill = isJsonObject(state) ? state.prefill : undefined;
  return isTemplateInput(prefill) ? prefill : null;
}
