import { HttpResponse, http } from "msw";
import { artifactResponse } from "@/api/mocks/artifactFiles";
import { apiError, db, noContent, notFound } from "@/api/mocks/db";
import { makeUpload } from "@/api/mocks/fixtures/factories";
import type { Run, Target, Upload } from "@/api/types";

const find = (id: unknown) => db.state.runs.find((run) => run.id === id);

function store(run: Run) {
  db.state.runs = db.state.runs.map((item) => (item.id === run.id ? run : item));
  return HttpResponse.json(run);
}

function withRun(id: unknown, change: (run: Run) => Run | Response) {
  const run = find(id);
  if (run === undefined) {
    return notFound("Run");
  }
  const result = change(run);
  return result instanceof Response ? result : store(result);
}

function skipReason(run: Run, target: Target): string | null {
  if (!run.languages.includes(target.language)) {
    return `Language ${target.language} is not in this run.`;
  }
  return db.state.channels.some((c) => c.id === target.channel_id)
    ? null
    : "The channel no longer exists.";
}

function uploadFor(run: Run, target: Target, variant: string): Upload {
  const reason = skipReason(run, target);
  return makeUpload({
    target_id: target.id,
    channel_id: target.channel_id,
    language: target.language,
    variant,
    ...(reason === null
      ? { youtube_video_id: `vid${Math.random().toString(36).slice(2, 10)}` }
      : { status: "skipped", youtube_video_id: null, url: null, error: reason, quota_units: 0 }),
  });
}

function uploadsFor(run: Run): Upload[] {
  const automation = db.state.automations.find((a) => a.id === run.automation_id);
  return (automation?.targets ?? []).flatMap((target) =>
    target.variants.map((variant) => uploadFor(run, target, variant)),
  );
}

function retry(run: Run, fromStage: string | undefined): Run {
  const index = Math.max(
    0,
    run.stages.findIndex((stage) => stage.stage_id === fromStage),
  );
  const stages = run.stages.map((stage, i) =>
    i < index ? stage : { ...stage, status: "pending" as const, message: null, finished_at: null },
  );
  return {
    ...run,
    status: "queued",
    stages,
    error: null,
    score: null,
    score_details: [],
    review: null,
    uploads: [],
    finished_at: null,
  };
}

export const runHandlers = [
  http.get("/api/runs", ({ request }) => {
    const query = new URL(request.url).searchParams;
    const automationId = query.get("automation_id");
    const status = query.get("status");
    const limit = Number(query.get("limit") ?? "100");
    const runs = db.state.runs
      .filter((run) => automationId === null || run.automation_id === automationId)
      .filter((run) => status === null || run.status === status)
      .slice(0, limit);
    return HttpResponse.json(runs);
  }),
  http.get("/api/runs/:id", ({ params }) => {
    const run = find(params.id);
    return run ? HttpResponse.json(run) : notFound("Run");
  }),
  http.get("/api/runs/:id/artifacts/:artifactId", ({ params }) => {
    const artifact = find(params.id)?.artifacts.find((item) => item.id === params.artifactId);
    return artifact ? artifactResponse(artifact) : notFound("Artifact");
  }),
  http.post("/api/runs/:id/retry", async ({ params, request }) => {
    const body = (await request.json().catch(() => ({}))) as { from_stage?: string };
    return withRun(params.id, (run) => retry(run, body.from_stage));
  }),
  http.post("/api/runs/:id/cancel", ({ params }) =>
    withRun(params.id, (run) => ({ ...run, status: "cancelled", finished_at: db.now() })),
  ),
  http.post("/api/runs/:id/review", async ({ params, request }) => {
    const body = (await request.json()) as { decision: "approved" | "rejected"; notes?: string };
    return withRun(params.id, (run) =>
      run.status !== "awaiting_review"
        ? apiError(409, "invalid_state", "Only a run awaiting review can be reviewed.")
        : {
            ...run,
            status: body.decision,
            review: { decision: body.decision, notes: body.notes ?? "", decided_at: db.now() },
          },
    );
  }),
  http.post("/api/runs/:id/publish", ({ params }) =>
    withRun(params.id, (run) =>
      run.status !== "approved"
        ? apiError(409, "invalid_state", "Only an approved run can be published.")
        : { ...run, status: "published", uploads: uploadsFor(run), finished_at: db.now() },
    ),
  ),
  http.delete("/api/runs/:id", ({ params }) => {
    db.state.runs = db.state.runs.filter((run) => run.id !== params.id);
    return noContent();
  }),
];
