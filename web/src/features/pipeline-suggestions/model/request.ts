import type { SuggestionRequest, TemplateAudience } from "@/api/types";
import { browserRegion, COMMON_REGIONS } from "@/features/pipeline-suggestions/model/regions";
import type { SelectOption } from "@/shared/ui";

export const OTHER_REGION = "other";
export const IDEA_COUNT_DEFAULT = 5;
export const IDEA_COUNT_MAX = 10;

export interface SuggestionForm {
  audience: TemplateAudience;
  region: string;
  otherRegion: string;
  category: string;
  count: number;
}

export const COUNT_OPTIONS: SelectOption[] = Array.from({ length: IDEA_COUNT_MAX }, (_, index) => {
  const value = String(index + 1);
  return { value, label: value };
});

function isCommonRegion(code: string): boolean {
  return (COMMON_REGIONS as readonly string[]).includes(code);
}

export function initialForm(locale: string | undefined): SuggestionForm {
  const region = browserRegion(locale);
  const common = isCommonRegion(region);
  return {
    audience: "kids",
    region: common ? region : OTHER_REGION,
    otherRegion: common ? "" : region,
    category: "",
    count: IDEA_COUNT_DEFAULT,
  };
}

export function chosenRegion(form: SuggestionForm): string {
  return form.region === OTHER_REGION ? form.otherRegion.trim().toUpperCase() : form.region;
}

export function suggestionRequest(form: SuggestionForm, engine: string): SuggestionRequest {
  return {
    engine,
    audience: form.audience,
    region: chosenRegion(form),
    category: form.category === "" ? null : form.category,
    count: form.count,
  };
}
