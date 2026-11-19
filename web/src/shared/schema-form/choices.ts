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
