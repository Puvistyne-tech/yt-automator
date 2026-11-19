import { ApiError } from "@/api/errors";
import { narratedEngine } from "@/api/mocks/fixtures/templateEngine";
import { BUILTIN_TEMPLATES, makeTemplate } from "@/api/mocks/fixtures/templates";
import type { TemplateSummary } from "@/api/types";
import { conflictNotice } from "@/features/pipeline-templates/model/conflicts";
import {
  draftFromTemplate,
  draftProblems,
  duplicateRequest,
  newTemplateDraft,
  settledDraft,
  templateInput,
} from "@/features/pipeline-templates/model/form";
import {
  canStartAutomation,
  openLabel,
  templateBadges,
  usageLabel,
} from "@/features/pipeline-templates/model/listing";

function summary(overrides: Partial<TemplateSummary> = {}): TemplateSummary {
  return { ...makeTemplate(), builtin: false, automations_using: 0, ...overrides };
}

describe("template listing", () => {
  it("badges built-ins, the audience and drafts", () => {
    const builtin = { ...summary(BUILTIN_TEMPLATES[0]), builtin: true };
    expect(templateBadges(builtin).map((b) => b.label)).toEqual(["Built-in", "For kids"]);
    expect(templateBadges(summary({ status: "draft" })).map((b) => b.label)).toEqual([
      "General audience",
      "Draft",
    ]);
  });

  it.each([
    [0, "Not used by any automation"],
    [1, "Used by 1 automation"],
    [3, "Used by 3 automations"],
  ])("describes %i automations using it", (count, label) => {
    expect(usageLabel(count)).toBe(label);
  });

  it("offers new automations only for ready pipelines and views built-ins", () => {
    expect(canStartAutomation(summary())).toBe(true);
    expect(canStartAutomation(summary({ status: "draft" }))).toBe(false);
    expect(openLabel(summary())).toBe("Edit");
    expect(openLabel(summary({ builtin: true }))).toBe("View");
  });
});

describe("template form", () => {
  it("starts a new draft from the engine's blank for the audience", () => {
    const draft = newTemplateDraft(narratedEngine, "kids");
    expect(draft).toMatchObject({ name: "", audience: "kids", status: "draft" });
    expect(draft.definition).toEqual(narratedEngine.blank.kids);
    expect(draft.definition).not.toBe(narratedEngine.blank.kids);
  });

  it("round-trips a template into a trimmed input with the chosen status", () => {
    const template = makeTemplate();
    const draft = { ...draftFromTemplate(template), name: "  Space  " };
    expect(templateInput(draft, template.engine, "draft")).toEqual({
      engine: template.engine,
      name: "Space",
      description: template.description,
      audience: "general",
      status: "draft",
      definition: template.definition,
    });
  });

  it.each([
    ["", { name: "Give the pipeline a name." }],
    ["   ", { name: "Give the pipeline a name." }],
    ["x".repeat(81), { name: "Keep the name to 80 characters or fewer." }],
    ["x".repeat(80), {}],
  ])("checks the name %j", (name, problems) => {
    expect(draftProblems({ ...newTemplateDraft(narratedEngine, "general"), name })).toEqual(
      problems,
    );
  });

  it("asks for a duplicate with only the choices made", () => {
    expect(duplicateRequest("  ", "kids")).toEqual({ audience: "kids" });
    expect(duplicateRequest(" Mine ", "general")).toEqual({ name: "Mine", audience: "general" });
  });
});

describe("settledDraft", () => {
  it("fills the schema defaults the form would add and keeps the chosen values", () => {
    const draft = draftFromTemplate(makeTemplate());
    const settled = settledDraft(draft, narratedEngine.definition_schema);
    expect(settled.definition).toMatchObject({ ...draft.definition, structure: "story" });
    expect(settledDraft(settled, narratedEngine.definition_schema)).toEqual(settled);
    expect(draft.definition).not.toHaveProperty("structure");
  });
});

describe("conflict notices", () => {
  it("titles each template conflict and keeps the server message", () => {
    const error = new ApiError(409, "template_in_use", "template is used by automations: A");
    expect(conflictNotice(error)).toEqual({
      title: "This pipeline is still in use",
      message: "template is used by automations: A",
    });
    expect(conflictNotice(new ApiError(409, "template_builtin", "m"))?.title).toBe(
      "Built-in pipelines cannot be changed",
    );
    expect(conflictNotice(new ApiError(409, "template_type_taken", "m"))?.title).toBe(
      "That pipeline type already exists",
    );
    expect(conflictNotice(new Error("other"))).toBeNull();
  });
});
