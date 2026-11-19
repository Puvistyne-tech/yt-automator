import type { FieldErrors } from "@/api/errors";
import type {
  DuplicateTemplateRequest,
  EngineSummary,
  JsonObject,
  PipelineTemplate,
  TemplateAudience,
  TemplateInput,
  TemplateStatus,
} from "@/api/types";

export const NAME_MAX_LENGTH = 80;

export interface TemplateDraft {
  name: string;
  description: string;
  audience: TemplateAudience;
  status: TemplateStatus;
  definition: JsonObject;
}

export function newTemplateDraft(engine: EngineSummary, audience: TemplateAudience): TemplateDraft {
  return {
    name: "",
    description: "",
    audience,
    status: "draft",
    definition: structuredClone(engine.blank[audience]),
  };
}

export function draftFromTemplate(template: PipelineTemplate): TemplateDraft {
  return {
    name: template.name,
    description: template.description,
    audience: template.audience,
    status: template.status,
    definition: structuredClone(template.definition),
  };
}

export function templateInput(
  draft: TemplateDraft,
  engine: string,
  status: TemplateStatus,
): TemplateInput {
  return { ...draft, engine, name: draft.name.trim(), status };
}

export function draftProblems(draft: TemplateDraft): FieldErrors {
  const name = draft.name.trim();
  if (name === "") {
    return { name: "Give the pipeline a name." };
  }
  return name.length > NAME_MAX_LENGTH
    ? { name: `Keep the name to ${NAME_MAX_LENGTH} characters or fewer.` }
    : {};
}

export function duplicateRequest(
  name: string,
  audience: TemplateAudience,
): DuplicateTemplateRequest {
  const trimmed = name.trim();
  return trimmed === "" ? { audience } : { name: trimmed, audience };
}
