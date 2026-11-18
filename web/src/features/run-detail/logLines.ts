import type { LogLevel, Run, RunLog } from "@/api/types";
import { humanizeId } from "@/shared/format/text";

export interface LogRow {
  key: string;
  at: string;
  level: LogLevel;
  stage: string;
  message: string;
}

const RUN_STAGE_LABEL = "Run";

function stageLabel(run: Run, stageId: string | null): string {
  if (stageId === null) {
    return RUN_STAGE_LABEL;
  }
  return run.stages.find((stage) => stage.stage_id === stageId)?.title ?? humanizeId(stageId);
}

function rowOf(run: Run, log: RunLog, index: number): LogRow {
  return {
    key: `${index}|${log.at}`,
    at: log.at,
    level: log.level,
    stage: stageLabel(run, log.stage_id),
    message: log.message,
  };
}

export function logRows(run: Run): LogRow[] {
  return run.logs.map((log, index) => rowOf(run, log, index));
}
