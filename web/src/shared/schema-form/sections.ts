export interface SectionSpec {
  title: string;
  fields: string[];
}

export interface Section<T> {
  title: string | null;
  properties: T[];
}

function isSectionSpec(value: unknown): value is SectionSpec {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate.title === "string" &&
    Array.isArray(candidate.fields) &&
    candidate.fields.every((field) => typeof field === "string")
  );
}

export function readSections(uiSchema: unknown): SectionSpec[] {
  if (typeof uiSchema !== "object" || uiSchema === null) {
    return [];
  }
  const raw = (uiSchema as Record<string, unknown>)["ui:sections"];
  return Array.isArray(raw) ? raw.filter(isSectionSpec) : [];
}

export function groupIntoSections<T extends { name: string }>(
  properties: T[],
  specs: SectionSpec[],
): Section<T>[] {
  if (specs.length === 0) {
    return [{ title: null, properties }];
  }
  const byName = new Map(properties.map((property) => [property.name, property]));
  const sections = specs
    .map((spec) => ({
      title: spec.title,
      properties: spec.fields.flatMap((field) => byName.get(field) ?? []),
    }))
    .filter((section) => section.properties.length > 0);
  const placed = new Set(specs.flatMap((spec) => spec.fields));
  const rest = properties.filter((property) => !placed.has(property.name));
  return rest.length > 0 ? [...sections, { title: null, properties: rest }] : sections;
}
