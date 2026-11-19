const NUMBERED_ITEM = /-(\d+)$/;

export function isArrayItem(path: readonly (string | number)[]): boolean {
  return typeof path[path.length - 1] === "number";
}

export function itemLabel(label: string): string {
  return label.replace(NUMBERED_ITEM, " $1");
}
