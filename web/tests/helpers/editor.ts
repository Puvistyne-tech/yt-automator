import { screen, within } from "@testing-library/react";
import { SETTINGS_VIEW_STORAGE_KEY } from "@/shared/settings-view/settingsView";

export function startInAllSettings() {
  window.localStorage.setItem(SETTINGS_VIEW_STORAGE_KEY, "all");
}

export async function findSection(name: string) {
  return within(await screen.findByRole("region", { name }));
}

export function sectionByName(name: string) {
  return within(screen.getByRole("region", { name }));
}

export function targetRow(index: number) {
  return within(screen.getByRole("listitem", { name: `Target ${index}` }));
}
