import { type TemplateConflictCode, templateConflictOf } from "@/api/templateErrors";

export interface ConflictNotice {
  title: string;
  message: string;
}

const CONFLICT_TITLES: Record<TemplateConflictCode, string> = {
  template_in_use: "This pipeline is still in use",
  template_builtin: "Built-in pipelines cannot be changed",
  template_type_taken: "That pipeline type already exists",
};

export function conflictNotice(error: unknown): ConflictNotice | null {
  const conflict = templateConflictOf(error);
  return conflict === null
    ? null
    : { title: CONFLICT_TITLES[conflict.code], message: conflict.message };
}
