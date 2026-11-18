import type { UseMutationResult } from "@tanstack/react-query";
import { useMutationNotifier } from "@/api/useMutationNotifier";
import type { ConfirmTarget } from "@/shared/ui";

type ConfirmableMutation<D, V> = Pick<
  UseMutationResult<D, Error, V, unknown>,
  "mutate" | "isPending"
>;

export interface ConfirmedMutationOptions<T, V, D> {
  confirm: ConfirmTarget<T>;
  mutation: ConfirmableMutation<D, V>;
  vars: (target: T) => V;
  success: (target: T) => string;
  onSuccess?: (data: D, target: T) => void;
}

export interface ConfirmedMutation {
  onConfirm: () => void;
  busy: boolean;
}

export function useConfirmedMutation<T, V, D>(
  options: ConfirmedMutationOptions<T, V, D>,
): ConfirmedMutation {
  const notifier = useMutationNotifier();
  const { confirm, mutation } = options;
  const onConfirm = () => {
    const target = confirm.target;
    if (target === null) {
      return;
    }
    mutation.mutate(
      options.vars(target),
      notifier.handlers<D>({
        success: options.success(target),
        onSuccess: (data) => options.onSuccess?.(data, target),
        onDone: confirm.cancel,
      }),
    );
  };
  return { onConfirm, busy: mutation.isPending };
}
