import { useState } from "react";
import { useNavigate } from "react-router";
import { useCancelRun, useDeleteRun } from "@/api/runs";
import type { Run } from "@/api/types";
import { useMutationNotifier } from "@/api/useMutationNotifier";

export type PendingAction = "cancel" | "delete" | "retry" | null;

export function useRunActionHandlers(run: Run) {
  const [pending, setPending] = useState<PendingAction>(null);
  const cancel = useCancelRun();
  const remove = useDeleteRun();
  const notifier = useMutationNotifier();
  const navigate = useNavigate();
  const close = () => setPending(null);
  const confirmCancel = () =>
    cancel.mutate(
      { id: run.id, vars: undefined },
      notifier.handlers({ success: "Run cancelled.", onDone: close }),
    );
  const confirmDelete = () =>
    remove.mutate(
      run.id,
      notifier.handlers({
        success: "Run deleted.",
        onSuccess: () => navigate("/runs"),
        onDone: close,
      }),
    );
  return {
    pending,
    open: setPending,
    close,
    confirmCancel,
    confirmDelete,
    cancelling: cancel.isPending,
    deleting: remove.isPending,
  };
}

export type RunActionHandlers = ReturnType<typeof useRunActionHandlers>;
