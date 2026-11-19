import { api } from "@/api/client";
import { db } from "@/api/mocks/db";
import { NO_TEXT_MODEL, TEXT_MODEL_UNAVAILABLE } from "@/api/mocks/templateSuggestions";
import type {
  SuggestionRequest,
  TemplateAudience,
  TemplateSuggestions,
  TemplateSummary,
} from "@/api/types";
import { disableWriters } from "../../helpers/providers";
import { disconnectChannels, onlyPlaceholderWriter } from "../../helpers/suggestions";
import { rejectionOf } from "../../helpers/templates";

const PATH = "/templates/suggestions";
const REQUEST: SuggestionRequest = { engine: "narrated_video", audience: "kids", region: "US" };

const suggest = (changes: Record<string, unknown> = {}) =>
  api.post<TemplateSuggestions>(PATH, { ...REQUEST, ...changes });

describe("mock template suggestions", () => {
  it("suggests drafts from YouTube trends with a connected channel and stores nothing", async () => {
    const reply = await suggest();

    expect(reply).toMatchObject({ source: "youtube", dropped: 1, provider: "ollama" });
    expect(reply.suggestions).toHaveLength(4);
    expect(new Set(reply.suggestions.map((s) => s.input.definition.structure)).size).toBe(4);
    expect(db.state.templates).toHaveLength(2);
  });

  it("reads the built-in sample trends when no channel is connected", async () => {
    disconnectChannels();
    expect((await suggest()).source).toBe("sample");
  });

  it.each<[TemplateAudience, number]>([
    ["kids", 1],
    ["general", 10],
  ])("returns %s drafts the create route accepts as suggested", async (audience, count) => {
    const reply = await suggest({ audience, count, category: "27" });
    expect(reply.suggestions.length + reply.dropped).toBeLessThanOrEqual(count);

    for (const suggestion of reply.suggestions) {
      expect(suggestion.based_on.length).toBeGreaterThan(0);
      const saved = await api.post<TemplateSummary>("/templates", suggestion.input);
      expect(saved).toMatchObject({ audience, origin: "suggested", status: "draft" });
    }
  });

  it.each<[string, Record<string, unknown>, Record<string, string>]>([
    ["an empty engine", { engine: "" }, { engine: "String should have at least 1 character" }],
    ["a missing engine", { engine: undefined }, { engine: "Field required" }],
    [
      "an unknown audience",
      { audience: "teens" },
      { audience: "Input should be 'kids' or 'general'" },
    ],
    ["a missing audience", { audience: undefined }, { audience: "Field required" }],
    [
      "a lower-case region",
      { region: "us" },
      { region: "String should match pattern '^[A-Z]{2}$'" },
    ],
    ["a missing region", { region: undefined }, { region: "Field required" }],
    [
      "a word category",
      { category: "music" },
      { category: "String should match pattern '^[0-9]{1,4}$'" },
    ],
    ["no ideas", { count: 0 }, { count: "Input should be greater than or equal to 1" }],
    ["too many ideas", { count: 11 }, { count: "Input should be less than or equal to 10" }],
    ["a fractional count", { count: 2.5 }, { count: "Input should be a valid integer" }],
    ["an engine not installed", { engine: "other" }, { engine: "engine 'other' is not installed" }],
    [
      "a bad region before the engine",
      { engine: "other", region: "U" },
      { region: "String should match pattern '^[A-Z]{2}$'" },
    ],
  ])("refuses %s on its field", async (_name, changes, fields) => {
    const refused = await rejectionOf(() => suggest(changes));
    expect(refused).toMatchObject({ status: 400, code: "validation_failed", fields });
  });

  it.each<[string, () => void, string]>([
    ["no text model is enabled", disableWriters, TEXT_MODEL_UNAVAILABLE],
    ["only a placeholder text model is enabled", onlyPlaceholderWriter, NO_TEXT_MODEL],
  ])("is unavailable when %s", async (_name, arrange, message) => {
    arrange();
    const refused = await rejectionOf(() => suggest());
    expect(refused).toMatchObject({ status: 409, code: "suggestions_unavailable", message });
  });
});
