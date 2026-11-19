import { screen, within } from "@testing-library/react";
import { db } from "@/api/mocks/db";
import { renderApp, type User } from "./renderApp";

const PLACEHOLDER_WRITER = "fake-llm";
export const PANEL = { name: "Suggest ideas" };
export const FIND = { name: "Find ideas" };

export function disconnectChannels() {
  db.state.channels = db.state.channels.map((channel) => ({ ...channel, status: "expired" }));
}

export function onlyPlaceholderWriter() {
  db.state.providerConfig = db.state.providerConfig.map((config) => ({
    ...config,
    chain: config.chain.map((choice) => ({
      ...choice,
      enabled: choice.provider_id === PLACEHOLDER_WRITER,
    })),
  }));
}

export function panel() {
  return within(screen.getByRole("region", PANEL));
}

export async function openSuggestions() {
  const app = renderApp("/pipelines");
  await app.user.click(await screen.findByRole("button", { name: "Suggest ideas" }));
  await screen.findByRole("region", PANEL);
  return app;
}

export async function findIdeas(user: User) {
  await user.click(panel().getByRole("button", FIND));
  return panel().findAllByRole("article");
}

export async function findIdea(user: User, name: string) {
  await findIdeas(user);
  return within(panel().getByRole("article", { name }));
}
