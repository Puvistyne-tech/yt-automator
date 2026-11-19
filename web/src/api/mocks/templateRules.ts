import { KIDS_CAPABILITY } from "@/api/capabilities";
import { ruleConflict } from "@/api/mocks/db";
import type { MockState } from "@/api/mocks/fixtures/seed";
import { BUILTIN_TEMPLATES } from "@/api/mocks/fixtures/templates";
import { automationsUsing } from "@/api/mocks/templateUsage";
import type {
  JsonObject,
  PipelineDescriptor,
  PipelineTemplate,
  TemplateInput,
  TemplateSummary,
} from "@/api/types";

type Errors = Record<string, string>;

const NAME_MAX_LENGTH = 80;
const COPY_SUFFIX = " (copy)";
const IMMUTABLE_FIELDS = ["audience", "engine"] as const;

export function nameErrors(name: string): Errors {
  const trimmed = name.trim();
  if (trimmed === "") {
    return { name: "name is required" };
  }
  return trimmed.length > NAME_MAX_LENGTH
    ? { name: `name must be at most ${NAME_MAX_LENGTH} characters` }
    : {};
}

export function copyName(name: string): string {
  return `${name
    .trim()
    .slice(0, NAME_MAX_LENGTH - COPY_SUFFIX.length)
    .trimEnd()}${COPY_SUFFIX}`;
}

export function originErrors(input: Pick<TemplateInput, "origin">): Errors {
  return input.origin === "builtin"
    ? { origin: "built-in templates come only from installed engines" }
    : {};
}

function definitionErrors(schema: JsonObject, definition: JsonObject): Errors {
  const known = Object.keys((schema.properties ?? {}) as JsonObject);
  const required = (schema.required ?? []) as string[];
  const unknown = Object.keys(definition).filter((key) => !known.includes(key));
  const missing = required.filter((key) => !(key in definition));
  return Object.fromEntries([
    ...unknown.map((key) => [`definition.${key}`, "Extra inputs are not permitted"]),
    ...missing.map((key) => [`definition.${key}`, "Field required"]),
  ]);
}

export function engineErrors(
  state: MockState,
  input: Pick<TemplateInput, "engine" | "definition">,
): Errors {
  const engine = state.engines.find((candidate) => candidate.engine_id === input.engine);
  return engine === undefined
    ? { engine: `engine '${input.engine}' is not installed` }
    : definitionErrors(engine.definition_schema, input.definition);
}

export function immutableErrors(current: PipelineTemplate, input: TemplateInput): Errors {
  return Object.fromEntries(
    IMMUTABLE_FIELDS.filter((field) => current[field] !== input[field]).map((field) => [
      field,
      `${field} cannot change after creation; duplicate the template instead`,
    ]),
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
    automations_using: automationsUsing(state, template.type_id).length,
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
