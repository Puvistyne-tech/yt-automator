import type { Run } from "@/api/types";

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
