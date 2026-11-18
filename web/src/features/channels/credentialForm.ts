import type { FieldErrors } from "@/api/errors";
import type { CredentialInput, CredentialPatch, CredentialSummary } from "@/api/types";
import { isIntegerAtLeast } from "@/shared/format/numbers";

export interface CredentialValues {
  name: string;
  client_id: string;
  client_secret: string;
  daily_quota_units: number;
}

export const DEFAULT_DAILY_QUOTA = 10_000;

export function credentialValues(credential: CredentialSummary | undefined): CredentialValues {
  return {
    name: credential?.name ?? "",
    client_id: credential?.client_id ?? "",
    client_secret: "",
    daily_quota_units: credential?.daily_quota_units ?? DEFAULT_DAILY_QUOTA,
  };
}

export function validateCredential(values: CredentialValues, isNew: boolean): FieldErrors {
  const errors: FieldErrors = {};
  if (values.name.trim() === "") {
    errors.name = "Give the credential a name.";
  }
  if (values.client_id.trim() === "") {
    errors.client_id = "Paste the OAuth client id.";
  }
  if (isNew && values.client_secret.trim() === "") {
    errors.client_secret = "Paste the OAuth client secret.";
  }
  if (!isIntegerAtLeast(values.daily_quota_units, 1)) {
    errors.daily_quota_units = "Use a whole number of units, at least 1.";
  }
  return errors;
}

export function credentialPayload(
  values: CredentialValues,
  isNew: boolean,
): CredentialInput | CredentialPatch {
  const base = {
    name: values.name.trim(),
    client_id: values.client_id.trim(),
    daily_quota_units: values.daily_quota_units,
  };
  const secret = values.client_secret.trim();
  if (isNew) {
    return { ...base, client_secret: secret };
  }
  return secret === "" ? base : { ...base, client_secret: secret };
}

export function credentialSecretHint(credential: CredentialSummary | undefined): string {
  if (credential === undefined) {
    return "Stored in the keychain. It is never shown again.";
  }
  return credential.has_secret
    ? "A secret is stored. Leave blank to keep it."
    : "No secret stored yet.";
}
