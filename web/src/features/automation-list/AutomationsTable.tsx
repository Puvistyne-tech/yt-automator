import { useAutomations } from "@/api/automations";
import { usePipelines } from "@/api/catalog";
import { useChannels } from "@/api/channels";
import type { Automation } from "@/api/types";
import { AutomationRow } from "@/features/automation-list/AutomationRow";
import { sortAutomations } from "@/features/automation-list/summary";
import type { DeleteFlow } from "@/features/automation-list/useDeleteFlow";
import { type ListActions, useListActions } from "@/features/automation-list/useListActions";
import {
  ACTIONS_COLUMN,
  ButtonLink,
  Card,
  ConfirmDialog,
  EmptyState,
  QueryState,
  Table,
} from "@/shared/ui";

const COLUMNS = ["Name", "Pipeline", "Targets", "Schedule", "Last run", "Enabled", ACTIONS_COLUMN];

function AutomationsEmpty() {
  return (
    <EmptyState
      icon="automations"
      title="No automations yet"
      description="An automation turns a pipeline into scheduled videos for your channels."
      action={
        <ButtonLink to="/automations/new" variant="primary" icon="plus">
          Create automation
        </ButtonLink>
      }
    />
  );
}

function AutomationsGrid({ list, actions }: { list: Automation[]; actions: ListActions }) {
  const pipelines = usePipelines();
  const channels = useChannels();
  return (
    <Table label="Automations" columns={COLUMNS}>
      {sortAutomations(list).map((automation) => (
        <AutomationRow
          key={automation.id}
          automation={automation}
          pipelines={pipelines.data ?? []}
          channels={channels.data ?? []}
          actions={actions}
        />
      ))}
    </Table>
  );
}

function DeleteAutomationDialog({ flow }: { flow: DeleteFlow }) {
  return (
    <ConfirmDialog
      {...flow.confirm.dialogProps}
      title="Delete automation?"
      message={`“${flow.confirm.target?.name ?? ""}” will stop running. Its past runs and uploads are kept.`}
      confirmLabel="Delete automation"
      busy={flow.busy}
      onConfirm={flow.onConfirm}
    />
  );
}

export function AutomationsTable() {
  const automations = useAutomations();
  const actions = useListActions();
  return (
    <Card flush>
      <QueryState
        query={automations}
        loadingLabel="Loading automations"
        isEmpty={(list) => list.length === 0}
        empty={<AutomationsEmpty />}
      >
        {(list) => <AutomationsGrid list={list} actions={actions} />}
      </QueryState>
      <DeleteAutomationDialog flow={actions.deleteFlow} />
    </Card>
  );
}
