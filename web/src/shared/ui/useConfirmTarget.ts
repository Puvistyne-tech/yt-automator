import { useCallback, useState } from "react";

export interface ConfirmTarget<T> {
  target: T | null;
  ask: (target: T) => void;
  cancel: () => void;
  dialogProps: { open: boolean; onCancel: () => void };
}

export function useConfirmTarget<T>(): ConfirmTarget<T> {
  const [target, setTarget] = useState<T | null>(null);
  const cancel = useCallback(() => setTarget(null), []);
  return {
    target,
    ask: (next: T) => setTarget(() => next),
    cancel,
    dialogProps: { open: target !== null, onCancel: cancel },
  };
}
