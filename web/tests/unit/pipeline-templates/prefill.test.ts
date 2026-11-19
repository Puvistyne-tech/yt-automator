import { narratedEngine } from "@/api/mocks/fixtures/templateEngine";
import { newPipelineState, prefilledInputOf } from "@/api/paths";
import type { TemplateInput } from "@/api/types";
import { draftFromInput, templateInput } from "@/features/pipeline-templates/model/form";
import { newTemplateStart } from "@/features/pipeline-templates/model/prefill";

const IDEA: TemplateInput = {
  engine: narratedEngine.engine_id,
  name: "Desk reset",
  description: "Quick routines.",
  audience: "general",
  status: "draft",
  origin: "suggested",
  definition: { structure: "list" },
};

const OTHER_ENGINE = { ...narratedEngine, engine_id: "other" };

describe("prefilled new pipelines", () => {
  it("reads a prefilled input back from the route state", () => {
    expect(prefilledInputOf(newPipelineState(IDEA))).toEqual(IDEA);
  });

  it.each([
    ["nothing", null],
    ["a string", "draft"],
    ["no prefill", {}],
    ["a prefill that is not an object", { prefill: 3 }],
    ["a missing name", { prefill: { ...IDEA, name: undefined } }],
    ["an unknown audience", { prefill: { ...IDEA, audience: "teens" } }],
    ["a definition that is a list", { prefill: { ...IDEA, definition: [] } }],
  ])("ignores %s", (_name, state) => {
    expect(prefilledInputOf(state)).toBeNull();
  });

  it("keeps the suggested origin from the draft to the saved input", () => {
    const draft = draftFromInput({ ...IDEA, status: "ready" });
    expect(draft).toEqual({
      name: "Desk reset",
      description: "Quick routines.",
      audience: "general",
      status: "draft",
      origin: "suggested",
      definition: { structure: "list" },
    });
    expect(templateInput(draft, IDEA.engine, "draft")).toEqual(IDEA);
  });

  it("leaves the origin out when the input has none", () => {
    const { origin: _origin, ...plain } = IDEA;
    expect(draftFromInput(plain)).not.toHaveProperty("origin");
  });

  it.each([
    ["the prefill's engine", [OTHER_ENGINE, narratedEngine], IDEA, narratedEngine, IDEA],
    [
      "the first engine without a prefill",
      [OTHER_ENGINE, narratedEngine],
      null,
      OTHER_ENGINE,
      null,
    ],
    ["the blank flow for an engine not installed", [OTHER_ENGINE], IDEA, OTHER_ENGINE, null],
  ])("starts with %s", (_name, engines, prefill, engine, kept) => {
    expect(newTemplateStart(engines, prefill)).toEqual({ engine, prefill: kept });
  });

  it("has no start without an engine", () => {
    expect(newTemplateStart([], IDEA)).toBeNull();
  });
});
