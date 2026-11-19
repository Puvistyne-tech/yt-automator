import { EMPTY_VALUE_MESSAGE } from "@/api/mocks/db";
import type { Errors } from "@/api/mocks/templateRules";

export const SUGGESTION_COUNT_DEFAULT = 5;
export const SUGGESTION_COUNT_MAX = 10;
const REGION_PATTERN = /^[A-Z]{2}$/;
const CATEGORY_PATTERN = /^[0-9]{1,4}$/;
const AUDIENCES: readonly unknown[] = ["kids", "general"];
const REQUIRED = "Field required";

export type SuggestionBody = Record<string, unknown>;

const patternMessage = (pattern: RegExp) => `String should match pattern '${pattern.source}'`;

function engineError(value: unknown): string | null {
  if (value === undefined) {
    return REQUIRED;
  }
  return typeof value === "string" && value !== "" ? null : EMPTY_VALUE_MESSAGE;
}

function audienceError(value: unknown): string | null {
  if (value === undefined) {
    return REQUIRED;
  }
  return AUDIENCES.includes(value) ? null : "Input should be 'kids' or 'general'";
}

function patternError(value: unknown, pattern: RegExp, optional: boolean): string | null {
  if (value === undefined || value === null) {
    return optional ? null : REQUIRED;
  }
  return typeof value === "string" && pattern.test(value) ? null : patternMessage(pattern);
}

function countError(value: unknown): string | null {
  if (value === undefined) {
    return null;
  }
  if (typeof value !== "number" || !Number.isInteger(value)) {
    return "Input should be a valid integer";
  }
  if (value < 1) {
    return "Input should be greater than or equal to 1";
  }
  return value > SUGGESTION_COUNT_MAX
    ? `Input should be less than or equal to ${SUGGESTION_COUNT_MAX}`
    : null;
}

export function suggestionRequestErrors(body: SuggestionBody): Errors {
  const found: [string, string | null][] = [
    ["engine", engineError(body.engine)],
    ["audience", audienceError(body.audience)],
    ["region", patternError(body.region, REGION_PATTERN, false)],
    ["category", patternError(body.category, CATEGORY_PATTERN, true)],
    ["count", countError(body.count)],
  ];
  return Object.fromEntries(found.filter((entry): entry is [string, string] => entry[1] !== null));
}
