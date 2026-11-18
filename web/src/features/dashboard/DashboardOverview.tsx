import { Link } from "react-router";
import { useDashboard } from "@/api/catalog";
import { RUN_STATUSES } from "@/api/labels";
import { useRuns } from "@/api/runs";
import type { Dashboard, DashboardRun, QuotaUsage } from "@/api/types";
import { formatRelative } from "@/shared/format/dates";
import { formatNumber, formatScore } from "@/shared/format/numbers";
import {
  ButtonLink,
  Card,
  EmptyState,
  ProgressMeter,
  QueryState,
  StatCard,
  StatusBadge,
  Table,
} from "@/shared/ui";
import "@/features/dashboard/dashboard.css";

function Stats({ data }: { data: Dashboard }) {
  return (
    <div className="stat-grid">
      <StatCard
        label="Automations"
        value={data.automations}
        hint={`${data.enabled_automations} enabled`}
      />
      <StatCard label="Channels" value={data.channels} />
      <StatCard label="Awaiting review" value={data.runs_awaiting_review} />
      <StatCard label="Runs today" value={data.runs_today} />
    </div>
  );
}

function ReviewQueue() {
  const runs = useRuns({ status: "awaiting_review", limit: 5 });
  return (
    <Card
      title="Waiting for your review"
      flush
      actions={
        <ButtonLink to="/runs?status=awaiting_review" size="sm" variant="ghost">
          View all
        </ButtonLink>
      }
    >
      <QueryState
        query={runs}
        isEmpty={(list) => list.length === 0}
        empty={
          <EmptyState
            icon="check"
            title="All caught up"
            description="Nothing is waiting for review."
          />
        }
      >
        {(list) => (
          <ul className="review-queue">
            {list.map((run) => (
              <li key={run.id}>
                <Link to={`/runs/${run.id}`} className="review-item">
                  <span className="cell-stack">
                    <span className="cell-title">{run.automation_name}</span>
                    <span className="subtle">
                      {formatRelative(run.created_at)} · score {formatScore(run.score)}
                    </span>
                  </span>
                  <span className="btn btn-secondary btn-sm">Review</span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </QueryState>
    </Card>
  );
}

function RecentRuns({ runs }: { runs: DashboardRun[] }) {
  if (runs.length === 0) {
    return (
      <EmptyState
        icon="runs"
        title="No runs yet"
        description="Runs appear here once an automation starts."
      />
    );
  }
  return (
    <Table label="Recent runs">
      <thead>
        <tr>
          <th scope="col">Automation</th>
          <th scope="col">Status</th>
          <th scope="col">Score</th>
          <th scope="col">Started</th>
        </tr>
      </thead>
      <tbody>
        {runs.map((run) => (
          <tr key={run.id}>
            <td>
              <Link to={`/runs/${run.id}`} className="cell-title">
                {run.automation_name}
              </Link>
            </td>
            <td>
              <StatusBadge {...RUN_STATUSES[run.status]} />
            </td>
            <td>{formatScore(run.score)}</td>
            <td>{formatRelative(run.created_at)}</td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
}

function Quota({ quota }: { quota: QuotaUsage[] }) {
  if (quota.length === 0) {
    return (
      <EmptyState
        icon="key"
        title="No credentials"
        description="Add a Google API project on the Channels page."
      />
    );
  }
  return (
    <div className="stack">
      {quota.map((item) => (
        <ProgressMeter
          key={item.credential_id}
          label={item.name}
          value={item.used}
          max={item.limit}
          detail={`${formatNumber(item.used)} / ${formatNumber(item.limit)} units`}
        />
      ))}
    </div>
  );
}

export function DashboardOverview() {
  const dashboard = useDashboard();
  return (
    <QueryState query={dashboard} loadingLabel="Loading dashboard">
      {(data) => (
        <div className="stack dashboard">
          <Stats data={data} />
          <div className="dashboard-grid">
            <Card
              title="Recent runs"
              flush
              actions={
                <ButtonLink to="/runs" size="sm" variant="ghost">
                  All runs
                </ButtonLink>
              }
            >
              <RecentRuns runs={data.recent_runs} />
            </Card>
            <div className="stack">
              <ReviewQueue />
              <Card title="YouTube quota today" description="Resets at midnight Pacific time.">
                <Quota quota={data.quota} />
              </Card>
            </div>
          </div>
        </div>
      )}
    </QueryState>
  );
}
