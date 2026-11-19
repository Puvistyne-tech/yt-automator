import { narratedEngine } from "@/api/mocks/fixtures/templateEngine";
import { YOUTUBE_CATEGORIES } from "@/features/pipeline-suggestions/model/categories";
import {
  browserRegion,
  COMMON_REGIONS,
  regionName,
} from "@/features/pipeline-suggestions/model/regions";
import {
  COUNT_OPTIONS,
  chosenRegion,
  initialForm,
  OTHER_REGION,
  type SuggestionForm,
  suggestionRequest,
} from "@/features/pipeline-suggestions/model/request";
import {
  droppedText,
  formatTitle,
  sourceText,
} from "@/features/pipeline-suggestions/model/results";

const FORM: SuggestionForm = {
  audience: "kids",
  region: "IN",
  otherRegion: "",
  category: "",
  count: 5,
};

describe("browserRegion", () => {
  it.each([
    ["en-IN", "IN"],
    ["fr-BE", "BE"],
    ["en", "US"],
    ["es-419", "US"],
    ["", "US"],
    [undefined, "US"],
    ["not a locale!", "US"],
  ])("reads %s as %s", (locale, region) => {
    expect(browserRegion(locale)).toBe(region);
  });
});

describe("regions and categories", () => {
  it("names regions in English and keeps a text that is not a code as it is", () => {
    expect(regionName("IN")).toBe("India");
    expect(regionName("in")).toBe("in");
    expect(regionName("")).toBe("");
  });

  it("lists unique common regions and categories with numeric ids", () => {
    expect(new Set(COMMON_REGIONS).size).toBe(COMMON_REGIONS.length);
    expect(YOUTUBE_CATEGORIES.every((c) => /^[0-9]{1,4}$/.test(c.id))).toBe(true);
    expect(YOUTUBE_CATEGORIES.find((c) => c.name === "Education")?.id).toBe("27");
  });
});

describe("suggestion form", () => {
  it.each([
    ["en-GB", { region: "GB", otherRegion: "" }],
    ["fr-BE", { region: OTHER_REGION, otherRegion: "BE" }],
    ["en", { region: "US", otherRegion: "" }],
  ])("starts %s in the matching country", (locale, region) => {
    expect(initialForm(locale)).toEqual({
      audience: "kids",
      category: "",
      count: 5,
      ...region,
    });
  });

  it.each<[Partial<SuggestionForm>, string]>([
    [{}, "IN"],
    [{ region: OTHER_REGION, otherRegion: " be " }, "BE"],
  ])("sends the chosen or typed country", (changes, region) => {
    expect(chosenRegion({ ...FORM, ...changes })).toBe(region);
  });

  it.each<[string, string | null]>([
    ["", null],
    ["27", "27"],
  ])("sends category %j as %j", (category, sent) => {
    expect(suggestionRequest({ ...FORM, category }, "narrated_video")).toEqual({
      engine: "narrated_video",
      audience: "kids",
      region: "IN",
      category: sent,
      count: 5,
    });
  });

  it("offers one to ten ideas", () => {
    expect(COUNT_OPTIONS.map((o) => o.value)).toEqual(
      Array.from({ length: 10 }, (_, i) => String(i + 1)),
    );
  });
});

describe("suggestion results", () => {
  it.each([
    ["youtube", "IN", "Based on what is trending on YouTube in India."],
    ["sample", "IN", "Based on built-in sample trends because no YouTube channel is connected."],
  ] as const)("explains the %s source", (source, region, text) => {
    expect(sourceText(source, region)).toBe(text);
  });

  it.each([
    [0, null],
    [1, "1 idea was left out because it did not pass the checks."],
    [3, "3 ideas were left out because they did not pass the checks."],
  ])("explains %i dropped ideas", (dropped, text) => {
    expect(droppedText(dropped)).toBe(text);
  });

  it.each([
    [{ structure: "quiz" }, "Quiz"],
    [{}, "Story"],
    [{ structure: "unknown" }, null],
  ])("names the format of %j", (definition, title) => {
    expect(formatTitle(narratedEngine, definition)).toBe(title);
  });

  it("has no format for an engine without one", () => {
    const engine = { ...narratedEngine, definition_schema: { type: "object" } };
    expect(formatTitle(engine, { structure: "quiz" })).toBeNull();
  });
});
