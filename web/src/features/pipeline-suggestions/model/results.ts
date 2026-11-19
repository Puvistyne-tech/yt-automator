import type { EngineSummary, JsonObject, TrendOrigin } from "@/api/types";
import { regionName } from "@/features/pipeline-suggestions/model/regions";
import { isJsonObject } from "@/shared/isJsonObject";

const FORMAT_FIELD = "structure";

export function sourceText(source: TrendOrigin, region: string): string {
  return source === "youtube"
    ? `Based on what is trending on YouTube in ${regionName(region)}.`
    : "Based on built-in sample trends because no YouTube channel is connected.";
}

export function droppedText(dropped: number): string | null {
  if (dropped === 0) {
    return null;
  }
  return dropped === 1
    ? "1 idea was left out because it did not pass the checks."
    : `${dropped} ideas were left out because they did not pass the checks.`;
}

function formatField(engine: EngineSummary): Record<string, unknown> | null {
  const properties = engine.definition_schema.properties;
  const field = isJsonObject(properties) ? properties[FORMAT_FIELD] : undefined;
  return isJsonObject(field) ? field : null;
}

export function formatTitle(engine: EngineSummary, definition: JsonObject): string | null {
  const field = formatField(engine);
  if (field === null) {
    return null;
  }
  const value = definition[FORMAT_FIELD] ?? field.default;
  const options: unknown[] = Array.isArray(field.oneOf) ? field.oneOf : [];
  const match = options.find((option) => isJsonObject(option) && option.const === value);
  return isJsonObject(match) && typeof match.title === "string" ? match.title : null;
}
