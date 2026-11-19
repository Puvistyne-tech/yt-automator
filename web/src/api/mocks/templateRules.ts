import { KIDS_CAPABILITY } from "@/api/capabilities";
import { ruleConflict } from "@/api/mocks/db";
import type { MockState } from "@/api/mocks/fixtures/seed";
import { BUILTIN_TEMPLATES } from "@/api/mocks/fixtures/templates";
import type {
  PipelineDescriptor,
  PipelineTemplate,
  TemplateInput,
  TemplateSummary,
} from "@/api/types";

const NAME_MAX_LENGTH = 80;
export const COPY_SUFFIX = " (copy)";
export const DELETE_REMEDY = "move the automations to another pipeline and finish their runs first";
export const DRAFT_REMEDY =
  "it must stay ready until they move to another pipeline and their runs finish";

export function nameErrors(name: string): Record<string, string> {
  const trimmed = name.trim();
  if (trimmed === "") {
    return { name: "name is required" };
  }
  return trimmed.length > NAME_MAX_LENGTH
    ? { name: `name must be at most ${NAME_MAX_LENGTH} characters` }
    : {};
}

export function definitionErrors(input: Pick<TemplateInput, "definition">): Record<string, string> {
  const brief = input.definition.brief;
  return typeof brief === "string" && brief.trim() === ""
    ? { "definition.brief": "Describe what the videos are about." }
    : {};
}

export function usersOf(state: MockState, typeId: string): string[] {
  return state.automations
    .filter((automation) => automation.pipeline_type === typeId)
    .map((automation) => automation.name)
    .sort();
}

export function inUseConflict(state: MockState, typeId: string, remedy: string) {
  const users = usersOf(state, typeId);
  return users.length === 0
    ? null
    : ruleConflict(
        "template_in_use",
        `template is used by automations: ${users.join(", ")}; ${remedy}`,
      );
}

export function builtinConflict(template: PipelineTemplate) {
  return ruleConflict(
    "template_builtin",
    `template '${template.name}' is built in and read-only; duplicate it to customise`,
  );
}

export function allTemplates(state: MockState): PipelineTemplate[] {
  return [...BUILTIN_TEMPLATES, ...state.templates];
}

export function summaryOf(state: MockState, template: PipelineTemplate): TemplateSummary {
  return {
    ...template,
    builtin: template.origin === "builtin",
    automations_using: usersOf(state, template.type_id).length,
  };
}

function templatePipeline(base: PipelineDescriptor, template: PipelineTemplate) {
  return {
    ...base,
    type_id: template.type_id,
    name: template.name,
    description: template.description,
    version: `1.0.0+r${template.revision}`,
    capabilities: template.audience === "kids" ? [KIDS_CAPABILITY] : [],
  };
}

export function servedPipelines(state: MockState): PipelineDescriptor[] {
  const [base] = state.pipelines;
  const ready = state.templates.filter((template) => template.status === "ready");
  return base === undefined
    ? state.pipelines
    : [...state.pipelines, ...ready.map((template) => templatePipeline(base, template))];
}
