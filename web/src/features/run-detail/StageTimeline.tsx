import { STAGE_STATUSES } from "@/api/labels";
import type { Run, StageRun } from "@/api/types";
import { stageProgress } from "@/features/run-detail/model";
import { formatDuration } from "@/shared/format/dates";
import { Card, Icon, type IconName, ProgressMeter, Spinner } from "@/shared/ui";

const MARKERS: Partial<Record<StageRun["status"], IconName>> = {
  done: "check",
  failed: "x",
  skipped: "right",
};

function Marker({ status }: { status: StageRun["status"] }) {
  const icon = MARKERS[status];
  return (
    <span className={`timeline-marker timeline-${status}`} aria-hidden="true">
      {status === "running" ? <Spinner size={12} /> : icon && <Icon name={icon} size={12} />}
    </span>
  );
}

function Stage({ stage }: { stage: StageRun }) {
  return (
    <li className={`timeline-item timeline-item-${stage.status}`}>
      <Marker status={stage.status} />
      <div className="timeline-content">
        <div className="row-between">
          <span className="timeline-title">{stage.title}</span>
          <span className="subtle">
            {stage.started_at
              ? formatDuration(stage.started_at, stage.finished_at)
              : STAGE_STATUSES[stage.status].label}
          </span>
        </div>
        <span className="visually-hidden">{STAGE_STATUSES[stage.status].label}</span>
        {stage.provider && <span className="subtle mono">{stage.provider}</span>}
        {stage.message && <span className="timeline-message">{stage.message}</span>}
      </div>
    </li>
  );
}

export function StageTimeline({ run }: { run: Run }) {
  const progress = stageProgress(run);
  return (
    <Card title="Stages">
      <div className="stack">
        <ProgressMeter
          label="Progress"
          value={progress.done}
          max={progress.total}
          tone={run.status === "failed" ? "danger" : "accent"}
          detail={`${progress.done} of ${progress.total}`}
        />
        <ol className="timeline" aria-label="Stage timeline">
          {run.stages.map((stage) => (
            <Stage key={stage.stage_id} stage={stage} />
          ))}
        </ol>
      </div>
    </Card>
  );
}
