import { AUDIENCE_LABELS, type Label } from "@/api/labels";
import type { TemplateSummary } from "@/api/types";
import { pluralize } from "@/shared/format/text";

export type TemplateBadge = Label;

export function templateBadges(template: TemplateSummary): TemplateBadge[] {
  const badges: TemplateBadge[] = [AUDIENCE_LABELS[template.audience]];
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
