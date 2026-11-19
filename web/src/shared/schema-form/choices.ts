import { isJsonObject } from "@/shared/isJsonObject";

export function offersNotSet(
  required: boolean | undefined,
  schema: { default?: unknown },
): boolean {
  return required !== true && (schema.default === undefined || schema.default === null);
}

export function unlistedValue(
  value: unknown,
  options: ReadonlyArray<{ value: unknown }>,
): string | null {
  if (typeof value !== "string" || value === "") {
    return null;
  }
  return options.some((option) => String(option.value) === value) ? null : value;
}

export interface SchemaChoice {
  value: string;
  title: string;
}

function propertySchema(schema: Record<string, unknown>, property: string) {
  const properties = schema.properties;
  const field = isJsonObject(properties) ? properties[property] : undefined;
  return isJsonObject(field) ? field : {};
}

export function choiceOptions(schema: Record<string, unknown>, property: string): SchemaChoice[] {
  const choices = propertySchema(schema, property).oneOf;
  return (Array.isArray(choices) ? choices : []).filter(isJsonObject).map((choice) => ({
    value: String(choice.const),
    title: String(choice.title ?? choice.const),
  }));
}

export function defaultChoice(schema: Record<string, unknown>, property: string): string | null {
  const fallback = propertySchema(schema, property).default;
  if (typeof fallback === "string") {
    return fallback;
  }
  return choiceOptions(schema, property)[0]?.value ?? null;
}

export function choiceTitle(
  schema: Record<string, unknown>,
  property: string,
  value: unknown,
): string | null {
  const match = choiceOptions(schema, property).find((choice) => choice.value === value);
  return match?.title ?? null;
}
