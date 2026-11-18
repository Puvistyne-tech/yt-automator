import type { LogLine, Run } from "@/api/types";

export function stageLines(run: Run): LogLine[] {
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

const lineKey = (line: LogLine) => `${line.stage_id}|${line.message}`;

export function mergeLogLines(stage: LogLine[], live: LogLine[]): LogLine[] {
  const seen = new Set(live.map(lineKey));
  return [...stage.filter((line) => !seen.has(lineKey(line))), ...live].sort((a, b) =>
    a.at.localeCompare(b.at),
  );
}
