import type { JsonObject } from "@/api/types/common";

export type TemplateAudience = "kids" | "general";
export type TemplateStatus = "draft" | "ready";
export type TemplateOrigin = "builtin" | "blank" | "duplicate" | "suggested";

export interface PipelineTemplate {
  id: string;
  type_id: string;
  engine: string;
  name: string;
  description: string;
  audience: TemplateAudience;
  status: TemplateStatus;
  origin: TemplateOrigin;
  revision: number;
  definition: JsonObject;
  created_at: string;
  updated_at: string;
}

export interface TemplateSummary extends PipelineTemplate {
  builtin: boolean;
  automations_using: number;
}

export interface TemplateInput {
  engine: string;
  name: string;
  description: string;
  audience: TemplateAudience;
  status: TemplateStatus;
  origin?: TemplateOrigin;
  definition: JsonObject;
}

export interface DuplicateTemplateRequest {
  name?: string;
  audience?: TemplateAudience;
}

export interface EngineSummary {
  engine_id: string;
  name: string;
  definition_schema: JsonObject;
  definition_ui_schema: JsonObject;
  blank: Record<TemplateAudience, JsonObject>;
}
