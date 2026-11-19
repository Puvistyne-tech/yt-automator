import { useCallback, useState } from "react";

function readStored(key: string): string | null {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

function writeStored(key: string, value: string): void {
  try {
    window.localStorage.setItem(key, value);
  } catch {
    return;
  }
}

export function useStoredChoice<T extends string>(
  key: string,
  parse: (stored: string | null) => T,
): readonly [T, (value: T) => void] {
  const [value, setValue] = useState<T>(() => parse(readStored(key)));
  const choose = useCallback(
    (next: T) => {
      setValue(next);
      writeStored(key, next);
    },
    [key],
  );
  return [value, choose] as const;
}
