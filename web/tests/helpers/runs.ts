import { screen, within } from "@testing-library/react";
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

export type UploadRow = Record<string, string>;

export function uploadRows(table: HTMLElement): UploadRow[] {
  const headers = within(table)
    .getAllByRole("columnheader")
    .map((header) => header.textContent ?? "");
  return within(table)
    .getAllByRole("row")
    .slice(1)
    .map((row) =>
      Object.fromEntries(
        within(row)
          .getAllByRole("cell")
          .map((cell, index) => [headers[index] ?? "", cell.textContent ?? ""]),
      ),
    );
}

export function audienceOf(rows: UploadRow[], channel: string, output: string): string[] {
  const row = rows.find((r) => r.Channel === channel && r.Output === output);
  return [row?.Privacy ?? "missing", row?.["Made for kids"] ?? "missing"];
}
