import { useDuplicateAutomation, useToggleAutomation } from "@/api/automations";
import type { Automation } from "@/api/types";
import { useMutationNotifier } from "@/api/useMutationNotifier";
import { useRunNow } from "@/api/useRunNow";
import { useDeleteFlow } from "@/features/automation-list/useDeleteFlow";

export function useListActions() {
  const notifier = useMutationNotifier();
  const toggle = useToggleAutomation();
  const runNow = useRunNow();
  const duplicate = useDuplicateAutomation();
  const deleteFlow = useDeleteFlow();
  return {
    deleteFlow,
    askDelete: deleteFlow.confirm.ask,
    setEnabled: (automation: Automation, enabled: boolean) =>
      toggle.mutate(
        { id: automation.id, enabled },
        notifier.handlers({ success: `${automation.name} ${enabled ? "enabled" : "paused"}.` }),
      ),
    runNow: runNow.start,
    duplicate: (automation: Automation) =>
      duplicate.mutate(
        automation.id,
        notifier.handlers({ success: (copy: Automation) => `Created “${copy.name}”.` }),
      ),
  };
}

export type ListActions = ReturnType<typeof useListActions>;
