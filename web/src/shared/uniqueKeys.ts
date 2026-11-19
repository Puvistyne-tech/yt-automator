export interface Keyed<T> {
  key: string;
  item: T;
}

export function withUniqueKeys<T>(items: readonly T[], keyOf: (item: T) => string): Keyed<T>[] {
  const seen = new Map<string, number>();
  return items.map((item) => {
    const base = keyOf(item);
    const count = (seen.get(base) ?? 0) + 1;
    seen.set(base, count);
    return { key: count === 1 ? base : `${base}#${count}`, item };
  });
}
