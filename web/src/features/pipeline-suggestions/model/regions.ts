export const COMMON_REGIONS = [
  "US",
  "GB",
  "IN",
  "CA",
  "AU",
  "DE",
  "FR",
  "ES",
  "BR",
  "MX",
  "JP",
  "ID",
] as const;

export const FALLBACK_REGION = "US";
const REGION_CODE = /^[A-Z]{2}$/;
const regionNames = new Intl.DisplayNames(["en"], { type: "region", fallback: "code" });

export function isRegionCode(code: string): boolean {
  return REGION_CODE.test(code);
}

export function regionName(code: string): string {
  return isRegionCode(code) ? (regionNames.of(code) ?? code) : code;
}

function localeRegion(locale: string): string | undefined {
  try {
    return new Intl.Locale(locale).region;
  } catch {
    return undefined;
  }
}

export function browserRegion(locale: string | undefined): string {
  const region = locale ? localeRegion(locale) : undefined;
  return region !== undefined && isRegionCode(region) ? region : FALLBACK_REGION;
}
