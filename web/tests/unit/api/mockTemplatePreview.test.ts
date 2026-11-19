import { api } from "@/api/client";
import { db } from "@/api/mocks/db";
import { engineFormats, sampleScript } from "@/api/mocks/fixtures/sampleScripts";
import { narratedEngine } from "@/api/mocks/fixtures/templateEngine";
import { engineLanguages } from "@/api/mocks/templatePreview";
import type { SampleScript, TemplatePreviewInput } from "@/api/types";
import { disableWriters } from "../../helpers/providers";
import { rejectionOf, TEMPLATE_INPUT } from "../../helpers/templates";

const PATH = "/templates/preview-script";

function previewBody(changes: Partial<TemplatePreviewInput> = {}): TemplatePreviewInput {
  return { ...TEMPLATE_INPUT, language: null, topic: "", ...changes };
}

const preview = (changes: Partial<TemplatePreviewInput> = {}) =>
  api.post<SampleScript>(PATH, previewBody(changes));

function withStructure(structure: string) {
  return previewBody({ definition: { structure } });
}

describe("mock template preview", () => {
  it("writes a sample in the first language with the first ready writer and stores nothing", async () => {
    const before = await api.get<unknown[]>("/templates");
    const sample = await preview({ topic: "  tides  " });

    expect(sample).toMatchObject({ language: "en", provider: "ollama" });
    expect(sample.title).toContain("tides");
    expect(sample.scenes.length).toBeGreaterThan(1);
    expect(await api.get<unknown[]>("/templates")).toEqual(before);
  });

  it.each(engineFormats(narratedEngine).map((format) => format.id))(
    "writes a %s sample shaped by its format",
    async (structure) => {
      const sample = await api.post<SampleScript>(PATH, withStructure(structure));
      expect(sample.scenes.every((scene) => scene.narration !== "")).toBe(true);
    },
  );

  it("gives headings to an explainer and none to a story", async () => {
    const explainer = await api.post<SampleScript>(PATH, withStructure("explainer"));
    const story = await api.post<SampleScript>(PATH, withStructure("story"));
    expect(explainer.scenes.every((scene) => scene.heading !== "")).toBe(true);
    expect(story.scenes.every((scene) => scene.heading === "")).toBe(true);
    expect(story.takeaway).not.toBe("");
  });

  it("falls back to a headed sample for a format without a canned shape", () => {
    const sample = sampleScript({ format: "timeline", topic: "", language: "en", provider: "x" });
    expect(sample.scenes[0]?.heading).not.toBe("");
    expect(sample.title).toContain("the night sky");
  });

  it.each<[string, Partial<TemplatePreviewInput>, Record<string, string>]>([
    [
      "topic",
      { topic: "x".repeat(301), name: "" },
      { topic: "String should have at most 300 characters" },
    ],
    ["name", { name: " ", language: "fr" }, { name: "name is required" }],
    [
      "name and definition",
      { name: " ", definition: { colour: "red" } },
      { name: "name is required" },
    ],
    ["language", { language: "fr" }, { language: "language must be one of: en, ta" }],
    [
      "definition",
      { definition: { colour: "red" } },
      { "definition.colour": "Extra inputs are not permitted" },
    ],
  ])("refuses a bad %s with only the first failing group", async (_name, changes, fields) => {
    const refused = await rejectionOf(() => preview(changes));
    expect(refused).toMatchObject({ status: 400, code: "validation_failed" });
    expect((refused as { fields: unknown }).fields).toEqual(fields);
  });

  it("offers the languages of the request engine's pipelines", () => {
    expect(engineLanguages(db.state, "narrated_video").map((option) => option.code)).toEqual([
      "en",
      "ta",
    ]);
    expect(engineLanguages(db.state, "other")).toEqual([]);
  });

  it("accepts a topic of exactly 300 characters and a chosen language", async () => {
    const sample = await preview({ topic: "y".repeat(300), language: "ta" });
    expect(sample.language).toBe("ta");
  });

  it("is unavailable when no text writer is ready", async () => {
    disableWriters();
    expect(await rejectionOf(() => preview())).toMatchObject({
      status: 409,
      code: "preview_unavailable",
      message: expect.stringMatching(/^The script writer is not available/),
    });
  });
});
