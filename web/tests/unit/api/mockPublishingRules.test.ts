import { AUTO_PUBLISH_STARTED, autoRejectMessage } from "@/api/automaticEvents";
import { DEFAULT_REVIEW_POLICY } from "@/api/automationDefaults";
import { api } from "@/api/client";
import { DELAY_OR_TIME, NEEDS_PUBLIC, NEVER_STARTS } from "@/api/mocks/automationRules";
import { afterApproval, autoRejected, scoredStatus } from "@/api/mocks/autoRules";
import { db } from "@/api/mocks/db";
import { makeAutomation, makeRun, makeTarget } from "@/api/mocks/fixtures/factories";
import { tick } from "@/api/mocks/simulator";
import type { Automation, AutomationInput, Run } from "@/api/types";

const failure = (call: Promise<unknown>) =>
  call.then(
    () => null,
    (error: unknown) => error,
  );

function inputFrom(automation: Automation): AutomationInput {
  const {
    id: _id,
    created_at: _c,
    updated_at: _u,
    next_run_at: _n,
    last_run: _l,
    ...input
  } = automation;
  return input;
}

const base = inputFrom(makeAutomation());
const auto = { ...DEFAULT_REVIEW_POLICY, mode: "auto_when_score_at_least" as const };

describe("mock automation rules", () => {
  it.each([
    [
      { review_policy: { ...auto, reject_below: 90 } },
      { "review_policy.reject_below": "must be below the minimum score for auto-approval (85)" },
    ],
    [
      { schedule: { ...base.schedule, active_from: "08:00" } },
      {
        "schedule.active_until": "set both the start and the end of the active hours, or neither",
      },
    ],
    [
      { schedule: { ...base.schedule, active_from: "08:00", active_until: "08:00" } },
      { "schedule.active_until": "must differ from the start of the active hours" },
    ],
    [
      { schedule: { ...base.schedule, active_from: "8", active_until: "09:00" } },
      { "schedule.active_from": "'8' is not a time of day: use a 24-hour time such as 08:00" },
    ],
    [
      {
        schedule: {
          ...base.schedule,
          kind: "cron" as const,
          cron: "0 3 * * *",
          active_from: "08:00",
          active_until: "20:00",
        },
      },
      { "schedule.active_from": NEVER_STARTS },
    ],
    [
      { schedule: { ...base.schedule, max_runs_per_day: 0 } },
      { "schedule.max_runs_per_day": "Input should be greater than or equal to 1" },
    ],
    [
      { retry_policy: { auto_retry_count: 11, retry_delay_minutes: -1 } },
      {
        "retry_policy.auto_retry_count": "Input should be less than or equal to 10",
        "retry_policy.retry_delay_minutes": "Input should be greater than or equal to 0",
      },
    ],
    [
      { targets: [makeTarget({ publish_time_of_day: "18:00", publish_delay_minutes: 5 })] },
      { "targets.0.publish_time_of_day": DELAY_OR_TIME },
    ],
    [
      { targets: [makeTarget({ publish_time_of_day: "18:00", privacy: "private" })] },
      { "targets.0.publish_time_of_day": NEEDS_PUBLIC },
    ],
    [
      { targets: [makeTarget({ publish_timezone: "Mars/Base" })] },
      { "targets.0.publish_timezone": "unknown timezone 'Mars/Base'" },
    ],
  ])("refuses %j like the backend", async (patch, fields) => {
    const error = await failure(api.post("/automations", { ...base, ...patch }));
    expect(error).toMatchObject({ status: 400, code: "validation_failed", fields });
  });

  it("accepts a fully configured automation", async () => {
    const target = makeTarget({ privacy: "public", publish_time_of_day: "18:00" });
    const schedule = { ...base.schedule, active_from: "08:00", active_until: "20:00" };
    const body = {
      ...base,
      targets: [target],
      schedule,
      review_policy: { ...auto, reject_below: 50 },
    };
    const created = await api.post<Automation>("/automations", body);
    expect(created.targets[0]?.publish_time_of_day).toBe("18:00");
    expect(created.schedule.active_from).toBe("08:00");
  });
});

describe("mock review rules", () => {
  const reviewRun = (patch: Partial<Run>) =>
    makeRun({ id: "run-x", automation_id: "auto-bedtime", ...patch });

  it("classifies a score like the backend", () => {
    const run = reviewRun({ review_policy: { ...auto, reject_below: 50 } });
    expect(scoredStatus(run, 49)).toBe("rejected");
    expect(scoredStatus(run, 60)).toBe("awaiting_review");
    expect(scoredStatus(run, 90)).toBe("approved");
  });

  it("records an automatic rejection in the review and the log", () => {
    const rejected = autoRejected(reviewRun({ review_policy: { ...auto, reject_below: 50 } }), 40);
    expect(rejected.status).toBe("rejected");
    expect(rejected.review?.notes).toBe(autoRejectMessage(40, 50));
    expect(rejected.logs.at(-1)?.level).toBe("warning");
  });

  it("publishes an approved run when auto-publish is on", () => {
    const policy = { ...DEFAULT_REVIEW_POLICY, auto_publish: true };
    const published = afterApproval(reviewRun({ status: "approved", review_policy: policy }));
    expect(published.status).toBe("published");
    expect(published.logs.map((entry) => entry.message)).toContain(AUTO_PUBLISH_STARTED);
    expect(afterApproval(reviewRun({ status: "approved" })).status).toBe("approved");
  });

  it("records when a scheduled public upload goes public", () => {
    const policy = { ...DEFAULT_REVIEW_POLICY, auto_publish: true };
    const timed = { privacy: "public" as const, publish_time_of_day: "18:00" };
    db.state.automations = db.state.automations.map((a) => ({
      ...a,
      targets: a.targets.map((target) => ({ ...target, ...timed })),
    }));
    const published = afterApproval(reviewRun({ status: "approved", review_policy: policy }));
    expect(published.uploads.every((upload) => upload.publish_at !== null)).toBe(true);
  });

  it("stops an auto-publish when every upload fails", () => {
    const policy = { ...DEFAULT_REVIEW_POLICY, auto_publish: true };
    const stopped = afterApproval(
      reviewRun({ status: "approved", review_policy: policy, languages: ["xx"] }),
    );
    expect(stopped.status).toBe("approved");
    expect(stopped.logs.at(-1)?.message).toBe("Auto-publish stopped: no upload succeeded");
  });

  it("stops an auto-publish without targets", () => {
    const policy = { ...DEFAULT_REVIEW_POLICY, auto_publish: true };
    db.state.automations = db.state.automations.map((a) => ({ ...a, targets: [] }));
    const stopped = afterApproval(reviewRun({ status: "approved", review_policy: policy }));
    expect(stopped.status).toBe("approved");
    expect(stopped.logs.at(-1)?.message).toBe(
      "Auto-publish stopped: run run-x has no publishable target",
    );
  });

  it("approving by hand publishes through the review endpoint", async () => {
    const policy = { ...DEFAULT_REVIEW_POLICY, auto_publish: true };
    db.state.runs = [reviewRun({ review_policy: policy })];
    const reviewed = await api.post<Run>("/runs/run-x/review", { decision: "approved" });
    expect(reviewed.status).toBe("approved");
    expect(db.state.publishQueue).toEqual(["run-x"]);
    tick();
    expect(db.state.runs[0]?.status).toBe("published");
    expect(db.state.publishQueue).toEqual([]);
  });

  it("approving by hand without auto-publish queues nothing", async () => {
    db.state.runs = [reviewRun({})];
    await api.post<Run>("/runs/run-x/review", { decision: "approved" });
    expect(db.state.publishQueue).toEqual([]);
  });

  it("drops a queued auto-publish for a deleted run", () => {
    db.state.publishQueue = ["run-gone"];
    db.state.runs = [];
    tick();
    expect(db.state.publishQueue).toEqual([]);
  });

  it("the simulator rejects a run under the threshold", () => {
    const policy = { ...DEFAULT_REVIEW_POLICY, reject_below: 90 };
    db.state.runs = [reviewRun({ status: "running", review_policy: policy, score: null })];
    tick();
    expect(db.state.runs[0]?.status).toBe("rejected");
  });
});
