import { useState } from "react";
import {
  useDeleteAutomation,
  useDuplicateAutomation,
  useRunAutomation,
  useToggleAutomation,
} from "@/api/automations";
import { errorMessage } from "@/api/errors";
import type { Automation } from "@/api/types";
import { useToast } from "@/shared/ui";

export function useListActions() {
  const toast = useToast();
  const toggle = useToggleAutomation();
  const run = useRunAutomation();
  const duplicate = useDuplicateAutomation();
  const remove = useDeleteAutomation();
  const [pendingDelete, setPendingDelete] = useState<Automation | null>(null);
  const fail = (error: unknown) => toast.error(errorMessage(error));

  return {
    pendingDelete,
    deleting: remove.isPending,
    askDelete: setPendingDelete,
    cancelDelete: () => setPendingDelete(null),
    confirmDelete: () => {
      const target = pendingDelete;
      if (target === null) {
        return;
      }
      remove.mutate(target.id, {
        onSuccess: () => toast.success(`Deleted “${target.name}”. Its runs are kept.`),
        onError: fail,
        onSettled: () => setPendingDelete(null),
      });
    },
    setEnabled: (automation: Automation, enabled: boolean) =>
      toggle.mutate(
        { id: automation.id, enabled },
        {
          onSuccess: () => toast.success(`${automation.name} ${enabled ? "enabled" : "paused"}.`),
          onError: fail,
        },
      ),
    runNow: (automation: Automation) =>
      run.mutate(automation.id, {
        onSuccess: () => toast.success(`Run queued for ${automation.name}.`),
        onError: fail,
      }),
    duplicate: (automation: Automation) =>
      duplicate.mutate(automation.id, {
        onSuccess: (copy) => toast.success(`Created “${copy.name}”.`),
        onError: fail,
      }),
  };
}

export type ListActions = ReturnType<typeof useListActions>;
