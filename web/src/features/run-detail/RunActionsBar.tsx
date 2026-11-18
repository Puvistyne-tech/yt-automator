import type { Run } from "@/api/types";
import { availableActions } from "@/features/run-detail/model";
import { RetryDialog } from "@/features/run-detail/RetryDialog";
import {
  type RunActionHandlers,
  useRunActionHandlers,
} from "@/features/run-detail/useRunActionHandlers";
import { Button, ConfirmDialog } from "@/shared/ui";

function RunActionDialogs({ run, handlers }: { run: Run; handlers: RunActionHandlers }) {
  return (
    <>
      <RetryDialog
        key={handlers.pending === "retry" ? "open" : "closed"}
        run={run}
        open={handlers.pending === "retry"}
        onClose={handlers.close}
      />
      <ConfirmDialog
        open={handlers.pending === "cancel"}
        title="Cancel this run?"
        message="The current stage stops and the run is marked cancelled."
        confirmLabel="Cancel run"
        cancelLabel="Keep running"
        busy={handlers.cancelling}
        onConfirm={handlers.confirmCancel}
        onCancel={handlers.close}
      />
      <ConfirmDialog
        open={handlers.pending === "delete"}
        title="Delete this run?"
        message="Its artifacts are removed from disk. Videos already on YouTube stay there."
        confirmLabel="Delete run"
        busy={handlers.deleting}
        onConfirm={handlers.confirmDelete}
        onCancel={handlers.close}
      />
    </>
  );
}

export function RunActionsBar({ run }: { run: Run }) {
  const actions = availableActions(run);
  const handlers = useRunActionHandlers(run);
  return (
    <div className="row">
      {actions.canCancel && (
        <Button icon="stop" onClick={() => handlers.open("cancel")}>
          Cancel run
        </Button>
      )}
      {actions.canRetry && (
        <Button icon="refresh" onClick={() => handlers.open("retry")}>
          Retry…
        </Button>
      )}
      {actions.canDelete && (
        <Button
          icon="trash"
          variant="ghost"
          className="btn-danger"
          onClick={() => handlers.open("delete")}
        >
          Delete
        </Button>
      )}
      <RunActionDialogs run={run} handlers={handlers} />
    </div>
  );
}
