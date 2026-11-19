import { ApiError } from "@/api/errors";

export const TEMPLATE_CONFLICT_CODES = [
  "template_builtin",
  "template_in_use",
  "template_type_taken",
] as const;

export type TemplateConflictCode = (typeof TEMPLATE_CONFLICT_CODES)[number];

export interface TemplateConflict {
  code: TemplateConflictCode;
  message: string;
}

function isConflictCode(code: string): code is TemplateConflictCode {
  return (TEMPLATE_CONFLICT_CODES as readonly string[]).includes(code);
}

export function templateConflictOf(error: unknown): TemplateConflict | null {
  if (!(error instanceof ApiError) || error.status !== 409 || !isConflictCode(error.code)) {
    return null;
  }
  return { code: error.code, message: error.message };
}

export const PREVIEW_UNAVAILABLE = "preview_unavailable";

export function previewUnavailableOf(error: unknown): string | null {
  const unavailable =
    error instanceof ApiError && error.status === 409 && error.code === PREVIEW_UNAVAILABLE;
  return unavailable ? error.message : null;
}
