import { screen, within } from "@testing-library/react";
import { renderApp, type User } from "./renderApp";
import { startNewPipeline } from "./templates";

export const PREVIEW = "/templates/preview-script";
export const WRITE = { name: "Write a sample script" };
export const SAMPLE = { name: /^Sample script/ };

export function previewCard() {
  return within(screen.getByRole("region", { name: "Try a sample script" }));
}

export async function openSaved(route: string) {
  const app = renderApp(route);
  await screen.findByRole("region", { name: "Try a sample script" });
  return app;
}

export async function newExplainer() {
  const app = await startNewPipeline("General audience");
  await app.user.type(screen.getByLabelText(/^Name/), "Sky facts");
  await app.user.selectOptions(screen.getByRole("combobox", { name: "Format" }), "explainer");
  return app;
}

export async function clickWrite(user: User) {
  await user.click(previewCard().getByRole("button", WRITE));
}

export async function writeSample(user: User, topic = "") {
  const field = previewCard().getByLabelText(/^Topic/);
  await user.clear(field);
  if (topic !== "") {
    await user.type(field, topic);
  }
  await clickWrite(user);
  return within(await screen.findByRole("article", SAMPLE));
}
