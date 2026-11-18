import { useDeleteAutomation } from "@/api/automations";
import type { Automation } from "@/api/types";
import { useMutationNotifier } from "@/api/useMutationNotifier";
import { useConfirmTarget } from "@/shared/ui";

export function useDeleteFlow() {
  const remove = useDeleteAutomation();
  const notifier = useMutationNotifier();
  const confirm = useConfirmTarget<Automation>();
  const confirmDelete = () => {
    const target = confirm.target;
    if (target !== null) {
      remove.mutate(
        target.id,
        notifier.handlers({
          success: `Deleted “${target.name}”. Its runs are kept.`,
          onDone: confirm.cancel,
        }),
      );
    }
  };
  return { confirm, deleting: remove.isPending, confirmDelete };
}

export type DeleteFlow = ReturnType<typeof useDeleteFlow>;
