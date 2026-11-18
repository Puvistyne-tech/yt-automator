export const GROUP_KEY = "x-group";
export const SWATCHES_KEY = "x-swatches";
export const SEARCH_FROM = 9;

const HEX_COLOUR = /^#[0-9a-fA-F]{6}$/;

export interface ChoiceSource {
  value: unknown;
  label: string;
  schema?: unknown;
}

export interface CardOption {
  value: unknown;
  label: string;
  description: string;
  group: string | null;
  swatches: string[];
}

export interface CardGroup {
  label: string | null;
  options: CardOption[];
}

function entryOf(schema: unknown): Record<string, unknown> {
  return typeof schema === "object" && schema !== null ? (schema as Record<string, unknown>) : {};
}

function textOf(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function swatchesOf(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.filter((item): item is string => typeof item === "string" && HEX_COLOUR.test(item));
}

export function cardOption(source: ChoiceSource): CardOption {
  const entry = entryOf(source.schema);
  const group = textOf(entry[GROUP_KEY]);
  return {
    value: source.value,
    label: source.label,
    description: textOf(entry.description),
    group: group === "" ? null : group,
    swatches: swatchesOf(entry[SWATCHES_KEY]),
  };
}

export function groupLabels(options: CardOption[]): string[] {
  const labels = options.flatMap((option) => (option.group === null ? [] : [option.group]));
  return [...new Set(labels)];
}

export function cardGroups(options: CardOption[]): CardGroup[] {
  const groups: CardGroup[] = [];
  for (const option of options) {
    const found = groups.find((group) => group.label === option.group);
    if (found) {
      found.options.push(option);
    } else {
      groups.push({ label: option.group, options: [option] });
    }
  }
  return groups;
}

function matches(option: CardOption, words: string[]): boolean {
  const haystack = `${option.label} ${option.description} ${option.group ?? ""}`.toLowerCase();
  return words.every((word) => haystack.includes(word));
}

export function filteredCards(
  options: CardOption[],
  query: string,
  group: string | null,
): CardOption[] {
  const words = query.toLowerCase().split(/\s+/).filter(Boolean);
  return options.filter(
    (option) => (group === null || option.group === group) && matches(option, words),
  );
}

export function offersSearch(count: number): boolean {
  return count >= SEARCH_FROM;
}

export function selectedLabel(options: CardOption[], value: unknown): string | null {
  return options.find((option) => String(option.value) === String(value))?.label ?? null;
}
