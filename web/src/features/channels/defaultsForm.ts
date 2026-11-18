import type { FieldErrors } from "@/api/errors";
import type { ChannelDefaults } from "@/api/types";

const REQUIRED: (keyof Pick<ChannelDefaults, "category_id" | "default_language">)[] = [
  "category_id",
  "default_language",
];

export function validateChannelDefaults(defaults: ChannelDefaults): FieldErrors {
  return Object.fromEntries(
    REQUIRED.filter((field) => defaults[field].trim() === "").map((field) => [field, "Required."]),
  );
}

export function channelDefaultsPayload(defaults: ChannelDefaults): ChannelDefaults {
  return {
    ...defaults,
    category_id: defaults.category_id.trim(),
    default_language: defaults.default_language.trim(),
  };
}
