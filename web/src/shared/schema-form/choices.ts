export function offersNotSet(
  required: boolean | undefined,
  schema: { default?: unknown },
): boolean {
  return required !== true && (schema.default === undefined || schema.default === null);
}
