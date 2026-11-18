import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import {
  AUTO_PUBLISH_STARTED,
  AUTO_PUBLISH_STOPPED_PREFIX,
  autoPublishStoppedMessage,
  autoRejectMessage,
  autoRetryMessage,
  skippedStartMessage,
  skippedStartTime,
} from "@/api/automaticEvents";
import { makeRun } from "@/api/mocks/fixtures/factories";
import type { RunLog } from "@/api/types";
import { automaticEvents } from "@/features/run-detail/automaticEventList";
import { formatDateTime } from "@/shared/format/dates";

const SAMPLES = resolve(process.cwd(), "..", "docs", "spec", "automatic-events.json");
const samples = JSON.parse(readFileSync(SAMPLES, "utf-8")) as {
  auto_reject: { score: number; threshold: number; message: string };
  auto_publish_started: { message: string };
  auto_publish_stopped: { reason: string; message: string };
  automatic_retry: {
    attempt: number;
    count: number;
    stage: string;
    failure: string;
    message: string;
  };
  skipped_start: { local: string; run_id: string; state: string; message: string };
};
const AT = "2026-01-05T10:00:00Z";
const log = (message: string): RunLog => ({ at: AT, level: "warning", stage_id: null, message });

describe("automatic events", () => {
  it("is empty for a run nothing happened to", () => {
    expect(automaticEvents(makeRun())).toEqual([]);
  });

  it("calls out an automatic rejection but not a rejection by hand", () => {
    const notes = autoRejectMessage(40, 50);
    const rejected = makeRun({
      status: "rejected",
      review: { decision: "rejected", notes, decided_at: AT },
    });
    expect(automaticEvents(rejected)).toEqual([
      { key: "rejected", tone: "danger", title: "Rejected automatically", detail: notes },
    ]);
    const byHand = {
      ...rejected,
      review: { decision: "rejected" as const, notes: "dark", decided_at: AT },
    };
    expect(automaticEvents(byHand)).toEqual([]);
  });

  it("shows a pending retry only while the run is failed", () => {
    const failed = makeRun({
      status: "failed",
      retry_at: AT,
      auto_retries: 1,
      retry_policy: { auto_retry_count: 3, retry_delay_minutes: 5 },
    });
    expect(automaticEvents(failed)).toEqual([
      {
        key: "retry-pending",
        tone: "info",
        title: "Retrying automatically",
        detail: `Attempt 2 of 3 starts at ${formatDateTime(AT)}, from the stage that failed.`,
      },
    ]);
    expect(automaticEvents({ ...failed, status: "queued" })).toEqual([]);
  });

  it("lists retries, skipped starts and stopped auto-publishes from the log", () => {
    const retry = autoRetryMessage(1, 2, "voice", "boom");
    const skipped = skippedStartMessage("2026-01-05 12:00 UTC", "run-1", "running");
    const stopped = `${AUTO_PUBLISH_STOPPED_PREFIX} daily quota too low`;
    const run = makeRun({ logs: [log(retry), log("ordinary"), log(skipped), log(stopped)] });
    expect(automaticEvents(run).map((event) => [event.key, event.title, event.detail])).toEqual([
      ["log-0", "Retried automatically", retry],
      ["log-2", "Scheduled start skipped", skipped],
      ["log-3", "Auto-publish stopped", stopped],
    ]);
  });

  it("matches the shared samples the backend also checks", () => {
    expect(autoRejectMessage(samples.auto_reject.score, samples.auto_reject.threshold)).toBe(
      samples.auto_reject.message,
    );
    expect(AUTO_PUBLISH_STARTED).toBe(samples.auto_publish_started.message);
    const stopped = samples.auto_publish_stopped;
    expect(autoPublishStoppedMessage(stopped.reason)).toBe(stopped.message);
    const retry = samples.automatic_retry;
    expect(autoRetryMessage(retry.attempt, retry.count, retry.stage, retry.failure)).toBe(
      retry.message,
    );
    const skipped = samples.skipped_start;
    expect(skippedStartMessage(skipped.local, skipped.run_id, skipped.state)).toBe(skipped.message);
    expect(skippedStartTime(skipped.message)).toBe(skipped.local);
    expect(skippedStartTime("Run failed")).toBeNull();
  });

  it("classifies every shared sample logged by the run", () => {
    const logged = [samples.automatic_retry, samples.skipped_start, samples.auto_publish_stopped];
    const run = makeRun({ logs: logged.map((sample) => log(sample.message)) });
    expect(automaticEvents(run).map((event) => event.title)).toEqual([
      "Retried automatically",
      "Scheduled start skipped",
      "Auto-publish stopped",
    ]);
  });

  it("ignores stage logs that look like automatic events", () => {
    const stageLog = { ...log(samples.automatic_retry.message), stage_id: "render" };
    expect(automaticEvents(makeRun({ logs: [stageLog] }))).toEqual([]);
  });
});
