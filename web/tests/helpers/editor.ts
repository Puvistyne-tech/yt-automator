import { screen, within } from "@testing-library/react";

export async function findSection(name: string) {
  return within(await screen.findByRole("region", { name }));
}

export function sectionByName(name: string) {
  return within(screen.getByRole("region", { name }));
}

export function targetRow(index: number) {
  return within(screen.getByRole("listitem", { name: `Target ${index}` }));
}
