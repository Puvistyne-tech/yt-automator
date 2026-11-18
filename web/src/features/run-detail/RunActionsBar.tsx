import { useState } from "react";
import { useNavigate } from "react-router";
import { errorMessage } from "@/api/errors";
import { useCancelRun, useDeleteRun, useRetryRun } from "@/api/runs";
import type { Run } from "@/api/types";
import {
  availableActions,
  defaultRetryStage,
  retryStageOptions,
} from "@/features/run-detail/model";
import { Button, ConfirmDialog, Dialog, FormField, Select, useToast } from "@/shared/ui";

type Pending = "cancel" | "delete" | "retry" | null;

function RetryDialog({ run, open, onClose }: { run: Run; open: boolean; onClose: () => void }) {
  const [stage, setStage] = useState(() => defaultRetryStage(run));
  const retry = useRetryRun();
  const toast = useToast();
  const submit = () =>
    retry.mutate(
      { id: run.id, vars: { from_stage: stage } },
      {
        onSuccess: () => toast.success("Retry queued."),
        onError: (error) => toast.error(errorMessage(error)),
        onSettled: onClose,
      },
    );
  return (
    <Dialog
      open={open}
      title="Retry run"
      description="Stages before the chosen one keep their artifacts."
      onClose={onClose}
      footer={
        <>
          <Button onClick={onClose}>Cancel</Button>
          <Button variant="primary" icon="refresh" loading={retry.isPending} onClick={submit}>
            Retry from stage
          </Button>
        </>
      }
    >
      <FormField label="Start from stage">
        <Select
          value={stage}
          options={retryStageOptions(run)}
          onChange={(e) => setStage(e.target.value)}
        />
      </FormField>
    </Dialog>
  );
}

export function RunActionsBar({ run }: { run: Run }) {
  const [pending, setPending] = useState<Pending>(null);
  const actions = availableActions(run);
  const cancel = useCancelRun();
  const remove = useDeleteRun();
  const toast = useToast();
  const navigate = useNavigate();
  const close = () => setPending(null);
  const fail = (error: unknown) => toast.error(errorMessage(error));
  const confirmCancel = () =>
    cancel.mutate(
      { id: run.id, vars: undefined },
      { onSuccess: () => toast.success("Run cancelled."), onError: fail, onSettled: close },
    );
  const confirmDelete = () =>
    remove.mutate(run.id, {
      onSuccess: () => {
        toast.success("Run deleted.");
        navigate("/runs");
      },
      onError: fail,
      onSettled: close,
    });
  return (
    <div className="row">
      {actions.canCancel && (
        <Button icon="stop" onClick={() => setPending("cancel")}>
          Cancel run
        </Button>
      )}
      {actions.canRetry && (
        <Button icon="refresh" onClick={() => setPending("retry")}>
          Retry…
        </Button>
      )}
      {actions.canDelete && (
        <Button
          icon="trash"
          variant="ghost"
          className="btn-danger"
          onClick={() => setPending("delete")}
        >
          Delete
        </Button>
      )}
      <RetryDialog
        key={pending === "retry" ? "open" : "closed"}
        run={run}
        open={pending === "retry"}
        onClose={close}
      />
      <ConfirmDialog
        open={pending === "cancel"}
        title="Cancel this run?"
        message="The current stage stops and the run is marked cancelled."
        confirmLabel="Cancel run"
        cancelLabel="Keep running"
        busy={cancel.isPending}
        onConfirm={confirmCancel}
        onCancel={close}
      />
      <ConfirmDialog
        open={pending === "delete"}
        title="Delete this run?"
        message="Its artifacts are removed from disk. Videos already on YouTube stay there."
        confirmLabel="Delete run"
        busy={remove.isPending}
        onConfirm={confirmDelete}
        onCancel={close}
      />
    </div>
  );
}
