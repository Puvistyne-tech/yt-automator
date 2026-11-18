import { useAutomations } from "@/api/automations";
import { usePipelines } from "@/api/catalog";
import { useChannels } from "@/api/channels";
import { AutomationRow } from "@/features/automation-list/AutomationRow";
import { sortAutomations } from "@/features/automation-list/summary";
import { useListActions } from "@/features/automation-list/useListActions";
import { ButtonLink, Card, ConfirmDialog, EmptyState, QueryState, Table } from "@/shared/ui";

const COLUMNS = ["Name", "Pipeline", "Targets", "Schedule", "Last run", "Enabled"];

export function AutomationsTable() {
  const automations = useAutomations();
  const pipelines = usePipelines();
  const channels = useChannels();
  const actions = useListActions();
  return (
    <Card flush>
      <QueryState
        query={automations}
        loadingLabel="Loading automations"
        isEmpty={(list) => list.length === 0}
        empty={
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
        }
      >
        {(list) => (
          <Table label="Automations">
            <thead>
              <tr>
                {COLUMNS.map((column) => (
                  <th key={column} scope="col">
                    {column}
                  </th>
                ))}
                <th scope="col" className="cell-actions">
                  <span className="visually-hidden">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {sortAutomations(list).map((automation) => (
                <AutomationRow
                  key={automation.id}
                  automation={automation}
                  pipelines={pipelines.data ?? []}
                  channels={channels.data ?? []}
                  actions={actions}
                />
              ))}
            </tbody>
          </Table>
        )}
      </QueryState>
      <ConfirmDialog
        open={actions.pendingDelete !== null}
        title="Delete automation?"
        message={`“${actions.pendingDelete?.name ?? ""}” will stop running. Its past runs and uploads are kept.`}
        confirmLabel="Delete automation"
        busy={actions.deleting}
        onConfirm={actions.confirmDelete}
        onCancel={actions.cancelDelete}
      />
    </Card>
  );
}
