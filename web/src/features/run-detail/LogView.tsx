import { useRunLogs } from "@/api/runs";
import type { LogLine, Run } from "@/api/types";
import { EmptyState } from "@/shared/ui";

function stageLines(run: Run): LogLine[] {
  return run.stages.flatMap((stage) =>
    stage.message && stage.finished_at
      ? [
          {
            at: stage.finished_at,
            message: stage.message,
            level: stage.status === "failed" ? "error" : "info",
            stage_id: stage.stage_id,
          },
        ]
      : [],
  );
}

export function mergeLogLines(stage: LogLine[], live: LogLine[]): LogLine[] {
  const seen = new Set(live.map((line) => `${line.stage_id}|${line.message}`));
  return [...stage.filter((line) => !seen.has(`${line.stage_id}|${line.message}`)), ...live].sort(
    (a, b) => a.at.localeCompare(b.at),
  );
}

const timeFormat = new Intl.DateTimeFormat("en-GB", {
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
});

export function LogView({ run }: { run: Run }) {
  const live = useRunLogs(run.id);
  const lines = mergeLogLines(stageLines(run), live.data ?? []);
  if (lines.length === 0) {
    return (
      <EmptyState
        icon="file"
        title="No log lines yet"
        description="Live log lines stream in while the run is open."
      />
    );
  }
  return (
    <div className="log-view" role="log" aria-label="Run log" aria-live="polite">
      {lines.map((line) => (
        <div
          key={`${line.at}|${line.stage_id}|${line.message}`}
          className={`log-line log-${line.level}`}
        >
          <time dateTime={line.at}>{timeFormat.format(new Date(line.at))}</time>
          <span className="log-stage">{line.stage_id ?? "run"}</span>
          <span className="log-message">{line.message}</span>
        </div>
      ))}
    </div>
  );
}
