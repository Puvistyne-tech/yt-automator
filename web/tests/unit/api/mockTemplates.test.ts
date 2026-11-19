import { api } from "@/api/client";
import { db } from "@/api/mocks/db";
import { servedPipelines } from "@/api/mocks/templateRules";
import type { PipelineDescriptor, TemplateInput, TemplateSummary } from "@/api/types";

const failure = (call: Promise<unknown>) =>
  call.then(
    () => null,
    (error: unknown) => error,
  );

const INPUT: TemplateInput = {
  engine: "narrated_video",
  name: "Space facts",
  description: "",
  audience: "general",
  status: "ready",
  definition: {},
};

describe("mock template handlers", () => {
  it.each([
    ["get", () => api.get("/templates/missing")],
    ["put", () => api.put("/templates/missing", INPUT)],
    ["delete", () => api.delete("/templates/missing")],
    ["duplicate", () => api.post("/templates/missing/duplicate", {})],
  ])("answers %s of an unknown template with not found", async (_name, call) => {
    expect(await failure(call())).toMatchObject({ status: 404, code: "template_not_found" });
  });

  it("refuses a blank or long name when creating", async () => {
    expect(await failure(api.post("/templates", { ...INPUT, name: " " }))).toMatchObject({
      status: 400,
      fields: { name: "name is required" },
    });
    expect(await failure(api.post("/templates", { ...INPUT, name: "x".repeat(81) }))).toMatchObject(
      { status: 400, fields: { name: "name must be at most 80 characters" } },
    );
  });

  it("refuses an audience change and keeps the stored origin on update", async () => {
    expect(
      await failure(api.put("/templates/space-facts", { ...INPUT, audience: "kids" })),
    ).toMatchObject({
      status: 400,
      fields: { audience: expect.stringContaining("cannot change") },
    });
    const saved = await api.put<TemplateSummary>("/templates/space-facts", {
      ...INPUT,
      origin: "suggested",
    });
    expect(saved).toMatchObject({ origin: "blank", revision: 4 });
  });

  it("duplicates without a body, keeping the audience and shortening long names", async () => {
    const long = "y".repeat(80);
    await api.put("/templates/history-five", { ...INPUT, name: long, status: "draft" });
    const copy = await api.post<TemplateSummary>("/templates/history-five/duplicate");
    expect(copy.name).toBe(`${"y".repeat(73)} (copy)`);
    expect(copy).toMatchObject({ audience: "general", type_id: `t_${copy.id}` });
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
