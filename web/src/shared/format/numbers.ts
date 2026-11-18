const UNITS = ["B", "KB", "MB", "GB", "TB"];

export function formatBytes(bytes: number): string {
  let value = Math.max(0, bytes);
  let unit = 0;
  while (value >= 1000 && unit < UNITS.length - 1) {
    value /= 1000;
    unit += 1;
  }
  const digits = unit === 0 || value >= 100 ? 0 : 1;
  return `${value.toFixed(digits)} ${UNITS[unit]}`;
}

export function formatNumber(value: number): string {
  return new Intl.NumberFormat("en-US").format(value);
}

export function formatScore(score: number | null | undefined): string {
  return score === null || score === undefined ? "—" : score.toFixed(score % 1 === 0 ? 0 : 1);
}

function isExactTenthsTie(value: number): boolean {
  const quarters = value * 4;
  return Number.isInteger(quarters) && quarters % 2 !== 0;
}

export function toOneDecimal(value: number): string {
  if (!isExactTenthsTie(value)) {
    return value.toFixed(1);
  }
  const lower = Math.floor(value * 10);
  const even = lower % 2 === 0 ? lower : lower + 1;
  return (even / 10).toFixed(1);
}

export function isIntegerAtLeast(value: number | null, min: number): boolean {
  return value !== null && Number.isInteger(value) && value >= min;
}
