import { useDeleteAutomation } from "@/api/automations";
import type { Automation } from "@/api/types";
import { useConfirmedMutation } from "@/api/useConfirmedMutation";
import { useConfirmTarget } from "@/shared/ui";

export function useDeleteFlow() {
  const confirm = useConfirmTarget<Automation>();
  const { onConfirm, busy } = useConfirmedMutation({
    confirm,
    mutation: useDeleteAutomation(),
    vars: (automation) => automation.id,
    success: (automation) => `Deleted “${automation.name}”. Its runs are kept.`,
  });
  return { confirm, onConfirm, busy };
}

export type DeleteFlow = ReturnType<typeof useDeleteFlow>;
