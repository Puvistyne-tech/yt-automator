import { useAutomations } from "@/api/automations";
import { usePipelines } from "@/api/catalog";
import { useChannels } from "@/api/channels";
import type { Automation } from "@/api/types";
import { AutomationRow } from "@/features/automation-list/AutomationRow";
import { ImportDialog } from "@/features/automation-list/ImportDialog";
import { sortAutomations } from "@/features/automation-list/summary";
import "@/features/automation-list/automation-list.css";
import type { DeleteFlow } from "@/features/automation-list/useDeleteFlow";
import { useImportFlow } from "@/features/automation-list/useImportFlow";
import { type ListActions, useListActions } from "@/features/automation-list/useListActions";
import {
  ACTIONS_COLUMN,
  Button,
  ButtonLink,
  Card,
  ConfirmDialog,
  EmptyState,
  QueryState,
  Table,
} from "@/shared/ui";

const COLUMNS = ["Name", "Pipeline", "Targets", "Schedule", "Last run", "Enabled", ACTIONS_COLUMN];

function AutomationsEmpty({ onImport }: { onImport: () => void }) {
  return (
    <EmptyState
      icon="automations"
      title="No automations yet"
      description="An automation turns a pipeline into scheduled videos for your channels."
      action={
        <div className="empty-actions">
          <ButtonLink to="/automations/new" variant="primary" icon="plus">
            Create automation
          </ButtonLink>
          <Button icon="upload" onClick={onImport}>
            Import from file
          </Button>
        </div>
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

function ImportButton({ onImport }: { onImport: () => void }) {
  return (
    <Button size="sm" icon="upload" onClick={onImport}>
      Import
    </Button>
  );
}

export function AutomationsTable() {
  const automations = useAutomations();
  const pipelines = usePipelines();
  const actions = useListActions();
  const importFlow = useImportFlow();
  return (
    <Card flush actions={<ImportButton onImport={importFlow.ask} />}>
      <QueryState
        query={automations}
        loadingLabel="Loading automations"
        isEmpty={(list) => list.length === 0}
        empty={<AutomationsEmpty onImport={importFlow.ask} />}
      >
        {(list) => <AutomationsGrid list={list} actions={actions} />}
      </QueryState>
      <DeleteAutomationDialog flow={actions.deleteFlow} />
      <ImportDialog flow={importFlow} pipelines={pipelines.data ?? []} />
    </Card>
  );
}
