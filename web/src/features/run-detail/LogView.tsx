import { useRunLogs } from "@/api/runs";
import type { Run } from "@/api/types";
import { mergeLogLines, stageLines } from "@/features/run-detail/logLines";
import { EmptyState } from "@/shared/ui";

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
