import { screen } from "@testing-library/react";
import { db } from "@/api/mocks/db";
import type { RunStatus } from "@/api/types";
import { renderApp } from "./renderApp";

export const storedRun = (id: string) => db.state.runs.find((r) => r.id === id);

export function setRunStatus(id: string, status: RunStatus) {
  db.state.runs = db.state.runs.map((r) => (r.id === id ? { ...r, status } : r));
}

export async function openRun(id: string) {
  const app = renderApp(`/runs/${id}`);
  await screen.findByRole("heading", { level: 1 });
  return app;
}
