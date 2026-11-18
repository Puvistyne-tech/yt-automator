import { HttpResponse, http } from "msw";
import { db, EMPTY_VALUE_MESSAGE, noContent, notFound, validationFailed } from "@/api/mocks/db";
import { makeRun, stagesWith } from "@/api/mocks/fixtures/factories";
import type { Automation, AutomationInput } from "@/api/types";

function inputErrors(input: AutomationInput): Record<string, string> {
  const errors: Record<string, string> = {};
  const pipeline = db.state.pipelines.find((p) => p.type_id === input.pipeline_type);
  if (input.name === "") {
    errors.name = EMPTY_VALUE_MESSAGE;
  }
  if (pipeline === undefined) {
    errors.pipeline_type = `unknown pipeline type '${input.pipeline_type}'`;
  }
  input.targets.forEach((target, index) => {
    if (!db.state.channels.some((channel) => channel.id === target.channel_id)) {
      errors[`targets.${index}.channel_id`] = `channel '${target.channel_id}' does not exist`;
    }
  });
  return errors;
}

function nextRunAt(input: AutomationInput): string | null {
  if (!input.enabled || input.schedule.kind === "manual") {
    return null;
  }
  const hours = input.schedule.kind === "interval" ? (input.schedule.every_hours ?? 1) : 24;
  return new Date(Date.now() + hours * 3_600_000).toISOString();
}

function build(input: AutomationInput, existing: Automation | undefined): Automation {
  const now = db.now();
  return {
    id: existing?.id ?? db.id("auto"),
    created_at: existing?.created_at ?? now,
    last_run: existing?.last_run ?? null,
    ...input,
    targets: input.targets.map((target) => ({ ...target, id: target.id ?? db.id("target") })),
    updated_at: now,
    next_run_at: nextRunAt(input),
  };
}

function save(input: AutomationInput, existing?: Automation) {
  const errors = inputErrors(input);
  if (Object.keys(errors).length > 0) {
    return validationFailed(errors);
  }
  const automation = build(input, existing);
  db.state.automations = existing
    ? db.state.automations.map((a) => (a.id === automation.id ? automation : a))
    : [...db.state.automations, automation];
  return HttpResponse.json(automation, { status: existing ? 200 : 201 });
}

const find = (id: unknown) => db.state.automations.find((a) => a.id === id);

export const automationHandlers = [
  http.get("/api/automations", () => HttpResponse.json(db.state.automations)),
  http.post("/api/automations", async ({ request }) =>
    save((await request.json()) as AutomationInput),
  ),
  http.get("/api/automations/:id", ({ params }) => {
    const automation = find(params.id);
    return automation ? HttpResponse.json(automation) : notFound("automation", params.id);
  }),
  http.put("/api/automations/:id", async ({ params, request }) => {
    const automation = find(params.id);
    return automation
      ? save((await request.json()) as AutomationInput, automation)
      : notFound("automation", params.id);
  }),
  http.patch("/api/automations/:id", async ({ params, request }) => {
    const automation = find(params.id);
    if (automation === undefined) {
      return notFound("automation", params.id);
    }
    const { enabled } = (await request.json()) as { enabled: boolean };
    const updated = { ...automation, enabled, next_run_at: nextRunAt({ ...automation, enabled }) };
    db.state.automations = db.state.automations.map((a) => (a.id === updated.id ? updated : a));
    return HttpResponse.json(updated);
  }),
  http.delete("/api/automations/:id", ({ params }) => {
    if (find(params.id) === undefined) {
      return notFound("automation", params.id);
    }
    db.state.automations = db.state.automations.filter((a) => a.id !== params.id);
    return noContent();
  }),
  http.post("/api/automations/:id/duplicate", ({ params }) => {
    const automation = find(params.id);
    if (automation === undefined) {
      return notFound("automation", params.id);
    }
    const copy = build(
      { ...automation, name: `${automation.name} (copy)`, enabled: false },
      undefined,
    );
    db.state.automations = [...db.state.automations, { ...copy, last_run: null }];
    return HttpResponse.json(copy, { status: 201 });
  }),
  http.post("/api/automations/:id/runs", ({ params }) => {
    const automation = find(params.id);
    if (automation === undefined) {
      return notFound("automation", params.id);
    }
    const run = makeRun({
      id: db.id("run"),
      automation_id: automation.id,
      automation_name: automation.name,
      status: "queued",
      trigger: "manual",
      languages: automation.languages,
      settings_snapshot: structuredClone(automation.settings),
      review_policy: { ...automation.review_policy },
      stages: stagesWith([]),
      artifacts: [],
      score: null,
      created_at: db.now(),
      started_at: null,
      finished_at: null,
    });
    db.state.runs = [run, ...db.state.runs];
    return HttpResponse.json(run, { status: 201 });
  }),
];
