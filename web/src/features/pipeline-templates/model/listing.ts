import type { TemplateAudience, TemplateSummary } from "@/api/types";
import { pluralize } from "@/shared/format/text";
import type { Tone } from "@/shared/ui";

export interface TemplateBadge {
  label: string;
  tone: Tone;
}

export const AUDIENCE_BADGES: Record<TemplateAudience, TemplateBadge> = {
  kids: { label: "For kids", tone: "accent" },
  general: { label: "General audience", tone: "neutral" },
};

export function templateBadges(template: TemplateSummary): TemplateBadge[] {
  const badges: TemplateBadge[] = [AUDIENCE_BADGES[template.audience]];
  if (template.builtin) {
    badges.unshift({ label: "Built-in", tone: "info" });
  }
  if (template.status === "draft") {
    badges.push({ label: "Draft", tone: "warning" });
  }
  return badges;
}

export function usageLabel(count: number): string {
  return count === 0 ? "Not used by any automation" : `Used by ${pluralize(count, "automation")}`;
}

export function canStartAutomation(template: TemplateSummary): boolean {
  return template.status === "ready";
}

export function openLabel(template: TemplateSummary): string {
  return template.builtin ? "View" : "Edit";
}
