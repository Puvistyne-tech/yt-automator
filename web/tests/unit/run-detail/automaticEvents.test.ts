import {
  AUTO_PUBLISH_STOPPED_PREFIX,
  autoRejectMessage,
  autoRetryMessage,
  skippedStartMessage,
  skippedStartTime,
} from "@/api/automaticEvents";
import { makeRun } from "@/api/mocks/fixtures/factories";
import type { RunLog } from "@/api/types";
import { automaticEvents } from "@/features/run-detail/automaticEvents";
import { formatDateTime } from "@/shared/format/dates";

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

  it("mirrors the backend's wording", () => {
    expect(autoRejectMessage(42.24, 50)).toBe(
      "Rejected automatically: the score 42.2 is below the auto-reject threshold 50",
    );
    expect(autoRetryMessage(1, 2, "render", "stage render failed: boom")).toBe(
      "Automatic retry 1 of 2 from stage render after: stage render failed: boom",
    );
    const skipped = skippedStartMessage("2026-01-05 12:00 UTC", "run-1", "queued");
    expect(skipped).toBe(
      "Scheduled start at 2026-01-05 12:00 UTC skipped: run run-1 is still queued",
    );
    expect(skippedStartTime(skipped)).toBe("2026-01-05 12:00 UTC");
    expect(skippedStartTime("Run failed")).toBeNull();
  });
});
