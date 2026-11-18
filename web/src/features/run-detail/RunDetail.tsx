import { useState } from "react";
import { Link } from "react-router";
import { usePipeline } from "@/api/catalog";
import { RUN_STATUSES } from "@/api/labels";
import type { Run } from "@/api/types";
import { ArtifactsView } from "@/features/run-detail/ArtifactsView";
import { LogView } from "@/features/run-detail/LogView";
import { availableActions } from "@/features/run-detail/model";
import { PublishPanel } from "@/features/run-detail/PublishPanel";
import { ReviewPanel } from "@/features/run-detail/ReviewPanel";
import { RunActionsBar } from "@/features/run-detail/RunActionsBar";
import { ScoreBreakdown } from "@/features/run-detail/ScoreBreakdown";
import { StageTimeline } from "@/features/run-detail/StageTimeline";
import { formatDateTime, formatDuration } from "@/shared/format/dates";
import { humanizeId } from "@/shared/format/numbers";
import { Card, Icon, PageHeader, StatusBadge, Tabs } from "@/shared/ui";
import "@/features/run-detail/run-detail.css";

function Details({ run }: { run: Run }) {
  const rows: [string, string][] = [
    ["Trigger", humanizeId(run.trigger)],
    ["Languages", run.languages.join(", ").toUpperCase()],
    ["Created", formatDateTime(run.created_at)],
    ["Duration", formatDuration(run.started_at, run.finished_at)],
  ];
  return (
    <Card title="Details">
      <dl className="details">
        {rows.map(([term, value]) => (
          <div key={term} className="details-row">
            <dt>{term}</dt>
            <dd>{value}</dd>
          </div>
        ))}
        {run.review && (
          <div className="details-row">
            <dt>Review</dt>
            <dd>
              {humanizeId(run.review.decision)}
              {run.review.notes ? ` — ${run.review.notes}` : ""}
            </dd>
          </div>
        )}
      </dl>
    </Card>
  );
}

function RunTabs({ run }: { run: Run }) {
  const [tab, setTab] = useState("artifacts");
  const pipeline = usePipeline(run.pipeline_type);
  const tabs = [
    {
      id: "artifacts",
      label: "Artifacts",
      count: run.artifacts.length,
      content: <ArtifactsView run={run} pipeline={pipeline.data} />,
    },
    { id: "score", label: "Score", content: <ScoreBreakdown run={run} /> },
    { id: "logs", label: "Logs", content: <LogView run={run} /> },
    {
      id: "settings",
      label: "Settings snapshot",
      content: <pre className="text-preview">{JSON.stringify(run.settings_snapshot, null, 2)}</pre>,
    },
  ];
  return (
    <Card>
      <Tabs label="Run details" tabs={tabs} value={tab} onChange={setTab} />
    </Card>
  );
}

export function RunDetail({ run }: { run: Run }) {
  const actions = availableActions(run);
  const showPublish = actions.canPublish || run.status === "publishing" || run.uploads.length > 0;
  return (
    <>
      <PageHeader
        back={
          <Link to="/runs" className="back-link">
            <Icon name="left" size={14} /> All runs
          </Link>
        }
        title={
          <span className="row run-title">
            {run.automation_name}
            <StatusBadge {...RUN_STATUSES[run.status]} />
          </span>
        }
        description={<Link to={`/automations/${run.automation_id}`}>Open automation</Link>}
        actions={<RunActionsBar run={run} />}
      />
      <div className="run-layout">
        <div className="stack run-main">
          {run.error && (
            <div className="banner banner-danger" role="alert">
              <Icon name="alert" />
              <span>{run.error}</span>
            </div>
          )}
          {actions.canReview && <ReviewPanel run={run} />}
          {showPublish && <PublishPanel run={run} canPublish={actions.canPublish} />}
          <RunTabs run={run} />
        </div>
        <aside className="stack run-side">
          <StageTimeline run={run} />
          <Details run={run} />
        </aside>
      </div>
    </>
  );
}
