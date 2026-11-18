import { HttpResponse, http } from "msw";
import { artifactResponse } from "@/api/mocks/artifactFiles";
import { afterApproval } from "@/api/mocks/autoRules";
import { db, noContent, notFound, ruleConflict } from "@/api/mocks/db";
import { publishRun } from "@/api/mocks/publish";
import { retriedRun } from "@/api/mocks/retry";
import { canCancel, canDelete, canRetry } from "@/api/runRules";
import type { Run } from "@/api/types";

const find = (id: unknown) => db.state.runs.find((run) => run.id === id);

function store(run: Run) {
  db.state.runs = db.state.runs.map((item) => (item.id === run.id ? run : item));
  return HttpResponse.json(run);
}

function withRun(id: unknown, change: (run: Run) => Run | Response) {
  const run = find(id);
  if (run === undefined) {
    return notFound("run", id);
  }
  const result = change(run);
  return result instanceof Response ? result : store(result);
}

function refuse(run: Run, target: string) {
  return ruleConflict(
    "invalid_run_transition",
    `run ${run.id} cannot move from ${run.status} to ${target}`,
  );
}

function retryOrRefuse(run: Run, fromStage: string | undefined): Run | Response {
  return canRetry(run.status) ? retriedRun(run, fromStage) : refuse(run, "queued");
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
    return run ? HttpResponse.json(run) : notFound("run", params.id);
  }),
  http.get("/api/runs/:id/artifacts/:artifactId", ({ params }) => {
    const artifact = find(params.id)?.artifacts.find((item) => item.id === params.artifactId);
    return artifact ? artifactResponse(artifact) : notFound("artifact", params.artifactId);
  }),
  http.post("/api/runs/:id/retry", async ({ params, request }) => {
    const body = (await request.json().catch(() => ({}))) as { from_stage?: string };
    return withRun(params.id, (run) => retryOrRefuse(run, body.from_stage));
  }),
  http.post("/api/runs/:id/cancel", ({ params }) =>
    withRun(params.id, (run) =>
      canCancel(run.status)
        ? { ...run, status: "cancelled", finished_at: db.now() }
        : refuse(run, "cancelled"),
    ),
  ),
  http.post("/api/runs/:id/review", async ({ params, request }) => {
    const body = (await request.json()) as { decision: "approved" | "rejected"; notes?: string };
    return withRun(params.id, (run) =>
      run.status !== "awaiting_review"
        ? ruleConflict(
            "run_not_awaiting_review",
            `run ${run.id} is ${run.status}, not awaiting review`,
          )
        : afterApproval({
            ...run,
            status: body.decision,
            review: { decision: body.decision, notes: body.notes ?? "", decided_at: db.now() },
          }),
    );
  }),
  http.post("/api/runs/:id/publish", ({ params }) =>
    withRun(params.id, (run) =>
      run.status !== "approved" ? refuse(run, "publishing") : publishRun(run),
    ),
  ),
  http.delete("/api/runs/:id", ({ params }) => {
    const run = find(params.id);
    if (run === undefined) {
      return notFound("run", params.id);
    }
    if (!canDelete(run.status)) {
      return ruleConflict(
        "run_active",
        `run ${run.id} is ${run.status}; cancel it before deleting`,
      );
    }
    db.state.runs = db.state.runs.filter((item) => item.id !== run.id);
    return noContent();
  }),
];
