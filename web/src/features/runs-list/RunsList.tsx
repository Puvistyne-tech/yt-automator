import { Link, useSearchParams } from "react-router";
import { useAutomations } from "@/api/automations";
import { RUN_STATUS_ORDER, RUN_STATUSES } from "@/api/labels";
import { useRuns } from "@/api/runs";
import type { Run } from "@/api/types";
import { hasActiveFilters, readFilters, withFilter } from "@/features/runs-list/filters";
import { formatDuration, formatRelative } from "@/shared/format/dates";
import { formatScore } from "@/shared/format/numbers";
import { humanizeId } from "@/shared/format/text";
import {
  Button,
  Card,
  EmptyState,
  FormField,
  QueryState,
  Select,
  StatusBadge,
  Table,
} from "@/shared/ui";

const RUN_COLUMNS = [
  "Automation",
  "Status",
  "Trigger",
  "Languages",
  "Score",
  "Started",
  "Duration",
];

const RUN_STATUS_OPTIONS = RUN_STATUS_ORDER.map((status) => ({
  value: status,
  label: RUN_STATUSES[status].label,
}));

function RunsTable({ runs }: { runs: Run[] }) {
  return (
    <Table label="Runs" columns={RUN_COLUMNS}>
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
          <td>{humanizeId(run.trigger)}</td>
          <td className="mono">{run.languages.join(", ").toUpperCase()}</td>
          <td>{formatScore(run.score)}</td>
          <td>{formatRelative(run.created_at)}</td>
          <td>{formatDuration(run.started_at, run.finished_at)}</td>
        </tr>
      ))}
    </Table>
  );
}

function Filters() {
  const [params, setParams] = useSearchParams();
  const filters = readFilters(params);
  const automations = useAutomations();
  const automationOptions = (automations.data ?? []).map((a) => ({ value: a.id, label: a.name }));
  return (
    <div className="filters">
      <FormField label="Automation">
        <Select
          value={filters.automation_id ?? ""}
          placeholder="All automations"
          options={automationOptions}
          onChange={(e) => setParams(withFilter(params, "automation_id", e.target.value))}
        />
      </FormField>
      <FormField label="Status">
        <Select
          value={filters.status ?? ""}
          placeholder="Any status"
          options={RUN_STATUS_OPTIONS}
          onChange={(e) => setParams(withFilter(params, "status", e.target.value))}
        />
      </FormField>
      {hasActiveFilters(filters) && (
        <Button variant="ghost" size="sm" icon="x" onClick={() => setParams(new URLSearchParams())}>
          Clear filters
        </Button>
      )}
    </div>
  );
}

export function RunsList() {
  const [params] = useSearchParams();
  const filters = readFilters(params);
  const runs = useRuns(filters);
  const filtered = hasActiveFilters(filters);
  return (
    <div className="stack">
      <Filters />
      <Card flush>
        <QueryState
          query={runs}
          loadingLabel="Loading runs"
          isEmpty={(list) => list.length === 0}
          empty={
            <EmptyState
              icon="runs"
              title={filtered ? "No runs match these filters" : "No runs yet"}
              description={
                filtered
                  ? "Try another status or automation."
                  : "Start one with Run now on the Automations page."
              }
            />
          }
        >
          {(list) => <RunsTable runs={list} />}
        </QueryState>
      </Card>
    </div>
  );
}
