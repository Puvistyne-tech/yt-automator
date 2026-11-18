import type { Run } from "@/api/types";
import { logRows } from "@/features/run-detail/logLines";
import { EmptyState } from "@/shared/ui";

const timeFormat = new Intl.DateTimeFormat("en-GB", {
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
});

export function LogView({ run }: { run: Run }) {
  const rows = logRows(run);
  if (rows.length === 0) {
    return (
      <EmptyState
        icon="file"
        title="No log lines yet"
        description="Log lines appear here as the run progresses."
      />
    );
  }
  return (
    <div className="log-view" role="log" aria-label="Run log" aria-live="polite">
      {rows.map((row) => (
        <div key={row.key} className={`log-line log-${row.level}`} data-level={row.level}>
          <time dateTime={row.at}>{timeFormat.format(new Date(row.at))}</time>
          <span className="log-stage">{row.stage}</span>
          <span className="log-message">{row.message}</span>
        </div>
      ))}
    </div>
  );
}
