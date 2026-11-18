import { Link } from "react-router";
import { RUN_STATUSES } from "@/api/labels";
import { runPath } from "@/api/paths";
import type { Automation, Channel, PipelineDescriptor } from "@/api/types";
import {
  languagesLabel,
  nextRunLabel,
  pipelineName,
  reconnectWarning,
  targetsLabel,
} from "@/features/automation-list/summary";
import type { ListActions } from "@/features/automation-list/useListActions";
import { formatRelative } from "@/shared/format/dates";
import { describeSchedule } from "@/shared/format/schedule";
import { ButtonLink, Icon, IconButton, StatusBadge, Switch } from "@/shared/ui";

interface AutomationRowProps {
  automation: Automation;
  pipelines: PipelineDescriptor[];
  channels: Channel[];
  actions: ListActions;
}

function LastRun({ automation }: { automation: Automation }) {
  const last = automation.last_run;
  if (last === null) {
    return <span className="subtle">Never run</span>;
  }
  return (
    <Link to={runPath(last)} className="cell-stack cell-link">
      <StatusBadge {...RUN_STATUSES[last.status]} />
      <span className="subtle">{formatRelative(last.created_at)}</span>
    </Link>
  );
}

function NameCell({ automation }: { automation: Automation }) {
  return (
    <td>
      <div className="cell-stack">
        <Link to={`/automations/${automation.id}`} className="cell-title">
          {automation.name}
        </Link>
        {automation.description && <span className="subtle clamp-1">{automation.description}</span>}
      </div>
    </td>
  );
}

function TargetsCell({
  automation,
  channels,
}: Pick<AutomationRowProps, "automation" | "channels">) {
  const warning = reconnectWarning(automation, channels);
  return (
    <td className="cell-wrap cell-narrow">
      <div className="cell-stack">
        <span>{targetsLabel(automation, channels)}</span>
        {warning && (
          <Link to="/channels" className="cell-warning">
            <Icon name="alert" size={14} /> {warning}
          </Link>
        )}
      </div>
    </td>
  );
}

function ScheduleCell({ automation }: { automation: Automation }) {
  return (
    <td className="cell-wrap cell-narrow">
      <div className="cell-stack">
        <span>{describeSchedule(automation.schedule)}</span>
        <span className="subtle">{nextRunLabel(automation)}</span>
      </div>
    </td>
  );
}

function RowActions({ automation, actions }: Pick<AutomationRowProps, "automation" | "actions">) {
  const name = automation.name;
  return (
    <td className="cell-actions">
      <IconButton
        icon="play"
        label={`Run ${name} now`}
        onClick={() => actions.runNow(automation)}
      />
      <ButtonLink
        to={`/automations/${automation.id}`}
        size="sm"
        variant="ghost"
        icon="edit"
        aria-label={`Edit ${name}`}
        className="btn-icon"
      />
      <IconButton
        icon="copy"
        label={`Duplicate ${name}`}
        onClick={() => actions.duplicate(automation)}
      />
      <IconButton
        icon="trash"
        variant="danger"
        label={`Delete ${name}`}
        onClick={() => actions.askDelete(automation)}
      />
    </td>
  );
}

export function AutomationRow({ automation, pipelines, channels, actions }: AutomationRowProps) {
  const pipeline = pipelines.find((p) => p.type_id === automation.pipeline_type);
  return (
    <tr>
      <NameCell automation={automation} />
      <td>
        <div className="cell-stack">
          <span>{pipelineName(pipelines, automation.pipeline_type)}</span>
          <span className="subtle">{languagesLabel(automation.languages, pipeline)}</span>
        </div>
      </td>
      <TargetsCell automation={automation} channels={channels} />
      <ScheduleCell automation={automation} />
      <td>
        <LastRun automation={automation} />
      </td>
      <td>
        <Switch
          checked={automation.enabled}
          ariaLabel={`Enable ${automation.name}`}
          onChange={(enabled) => actions.setEnabled(automation, enabled)}
        />
      </td>
      <RowActions automation={automation} actions={actions} />
    </tr>
  );
}
