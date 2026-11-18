import type { FieldErrors } from "@/api/errors";

export const EDITOR_SECTIONS = [
  { id: "general", title: "General" },
  { id: "content", title: "Content" },
  { id: "languages", title: "Languages" },
  { id: "targets", title: "Targets" },
  { id: "schedule", title: "Schedule" },
  { id: "review", title: "Review" },
] as const;

export type EditorSectionId = (typeof EDITOR_SECTIONS)[number]["id"];

const PREFIXES: [string, EditorSectionId][] = [
  ["settings", "content"],
  ["languages", "languages"],
  ["targets", "targets"],
  ["schedule", "schedule"],
  ["retry_policy", "schedule"],
  ["review_policy", "review"],
];

export function sectionOf(path: string): EditorSectionId {
  const head = path.split(".")[0] ?? "";
  return PREFIXES.find(([prefix]) => prefix === head)?.[1] ?? "general";
}

export function errorCounts(errors: FieldErrors): Record<EditorSectionId, number> {
  const counts: Record<EditorSectionId, number> = {
    general: 0,
    content: 0,
    languages: 0,
    targets: 0,
    schedule: 0,
    review: 0,
  };
  for (const path of Object.keys(errors)) {
    counts[sectionOf(path)] += 1;
  }
  return counts;
}

export function firstErrorSection(errors: FieldErrors): EditorSectionId | null {
  const counts = errorCounts(errors);
  return EDITOR_SECTIONS.find((section) => counts[section.id] > 0)?.id ?? null;
}

export function sectionAnchor(id: EditorSectionId): string {
  return `editor-section-${id}`;
}
