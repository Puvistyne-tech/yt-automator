import type { EngineSummary, JsonObject, TrendOrigin } from "@/api/types";
import { regionName } from "@/features/pipeline-suggestions/model/regions";
import { choiceTitle, defaultChoice } from "@/shared/schema-form/choices";

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

export function formatTitle(engine: EngineSummary, definition: JsonObject): string | null {
  const schema = engine.definition_schema;
  const value = definition[FORMAT_FIELD] ?? defaultChoice(schema, FORMAT_FIELD);
  return choiceTitle(schema, FORMAT_FIELD, value);
}
