import { api } from "@/api/client";
import { db } from "@/api/mocks/db";
import { copyName, servedPipelines } from "@/api/mocks/templateRules";
import { DELETE_REMEDY, isOpenRun } from "@/api/mocks/templateUsage";
import type { PipelineDescriptor, RunStatus, TemplateSummary } from "@/api/types";
import { itemAt } from "../../helpers/itemAt";
import { rejectionOf, TEMPLATE_INPUT } from "../../helpers/templates";

function holdWithRun(typeId: string, status: RunStatus, retryAt: string | null = null) {
  const run = itemAt(db.state.runs, 0);
  Object.assign(run, { pipeline_type: typeId, status, retry_at: retryAt });
  return run.id;
}

describe("mock template handlers", () => {
  it.each([
    ["get", () => api.get("/templates/missing")],
    ["put", () => api.put("/templates/missing", TEMPLATE_INPUT)],
    ["delete", () => api.delete("/templates/missing")],
    ["duplicate", () => api.post("/templates/missing/duplicate", {})],
  ])("answers %s of an unknown template with not found", async (_name, call) => {
    expect(await rejectionOf(call)).toMatchObject({ status: 404, code: "template_not_found" });
  });

  it("refuses a built-in origin, a missing engine and unknown definition keys together", async () => {
    const input = { ...TEMPLATE_INPUT, origin: "builtin", name: " " };
    expect(await rejectionOf(() => api.post("/templates", input))).toMatchObject({
      status: 400,
      fields: {
        origin: "built-in templates come only from installed engines",
        name: "name is required",
      },
    });
    const elsewhere = { ...TEMPLATE_INPUT, engine: "other" };
    expect(await rejectionOf(() => api.post("/templates", elsewhere))).toMatchObject({
      fields: { engine: "engine 'other' is not installed" },
    });
    const extra = { ...TEMPLATE_INPUT, definition: { colour: "red" } };
    expect(await rejectionOf(() => api.post("/templates", extra))).toMatchObject({
      fields: { "definition.colour": "Extra inputs are not permitted" },
    });
  });

  it("refuses audience and engine changes and keeps the stored origin on update", async () => {
    const changed = { ...TEMPLATE_INPUT, audience: "kids", engine: "other" };
    const suffix = "cannot change after creation; duplicate the template instead";
    expect(await rejectionOf(() => api.put("/templates/space-facts", changed))).toMatchObject({
      status: 400,
      fields: { audience: `audience ${suffix}`, engine: `engine ${suffix}` },
    });
    const saved = await api.put<TemplateSummary>("/templates/space-facts", {
      ...TEMPLATE_INPUT,
      origin: "suggested",
    });
    expect(saved).toMatchObject({ origin: "blank", revision: 4, status: "ready" });
  });

  it("names the open runs that hold an unused template", async () => {
    const run = holdWithRun("t_history-five", "queued");
    expect(await rejectionOf(() => api.delete("/templates/history-five"))).toMatchObject({
      status: 409,
      message: `template is used by open runs: ${run}; ${DELETE_REMEDY}`,
    });
  });

  it("names automations and open runs, joined with and", async () => {
    const run = holdWithRun("t_space-facts", "failed", "2030-01-01T00:00:00Z");
    expect(await rejectionOf(() => api.delete("/templates/space-facts"))).toMatchObject({
      code: "template_in_use",
      message: `template is used by automations: Space facts weekly and open runs: ${run}; ${DELETE_REMEDY}`,
    });
  });

  it.each<[RunStatus, string | null, boolean]>([
    ["awaiting_review", null, true],
    ["approved", null, true],
    ["publishing", null, true],
    ["failed", "2030-01-01T00:00:00Z", true],
    ["failed", null, false],
    ["published", null, false],
  ])("counts a %s run with retry %s as open: %s", (status, retryAt, open) => {
    expect(isOpenRun({ status, retry_at: retryAt })).toBe(open);
  });

  it("duplicates without a body and trims before shortening the copy name", async () => {
    const copy = await api.post<TemplateSummary>("/templates/history-five/duplicate");
    expect(copy).toMatchObject({ audience: "general", type_id: `t_${copy.id}` });
    expect(copyName(`  ${"y".repeat(72)}  z`)).toBe(`${"y".repeat(72)} (copy)`);
  });

  it("serves ready templates as pipeline types with their audience", async () => {
    const types = (await api.get<PipelineDescriptor[]>("/pipelines")).map((p) => [
      p.type_id,
      p.capabilities,
    ]);
    expect(types).toEqual([
      ["kids_story", ["kids_content"]],
      ["t_space-facts", []],
    ]);
    db.state.templates = db.state.templates.map((t) => ({ ...t, audience: "kids" as const }));
    expect(servedPipelines(db.state)[1]?.capabilities).toEqual(["kids_content"]);
    expect(servedPipelines({ ...db.state, pipelines: [] })).toEqual([]);
  });
});
