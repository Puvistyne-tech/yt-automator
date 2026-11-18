import { type Dispatch, type SetStateAction, useCallback, useState } from "react";

export function usePatchState<T extends object>(
  initial: T | (() => T),
): readonly [T, (patch: Partial<T>) => void, Dispatch<SetStateAction<T>>] {
  const [value, setValue] = useState<T>(initial);
  const patch = useCallback((change: Partial<T>) => {
    setValue((current) => ({ ...current, ...change }));
  }, []);
  return [value, patch, setValue] as const;
}
