import type { JsonObject } from "@/api/types/common";

export type Aspect = "16:9" | "9:16";

export interface StageDescriptor {
  id: string;
  title: string;
  description: string;
}

export interface LanguageOption {
  code: string;
  name: string;
}

export interface VariantOption {
  id: string;
  name: string;
  aspect: Aspect;
  description: string;
}

export interface PipelineDescriptor {
  type_id: string;
  name: string;
  description: string;
  version: string;
  settings_schema: JsonObject;
  default_settings: JsonObject;
  ui_schema: JsonObject;
  stages: StageDescriptor[];
  languages: LanguageOption[];
  variants: VariantOption[];
  capabilities: string[];
}
