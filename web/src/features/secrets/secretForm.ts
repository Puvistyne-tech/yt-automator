export type SecretCheck = { ok: true; value: string } | { ok: false; error: string };

export function validateSecretValue(value: string): SecretCheck {
  const trimmed = value.trim();
  return trimmed === "" ? { ok: false, error: "Enter a value." } : { ok: true, value: trimmed };
}
