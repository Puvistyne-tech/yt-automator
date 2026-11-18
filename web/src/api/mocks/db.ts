import { HttpResponse } from "msw";
import { type MockState, seedState } from "@/api/mocks/fixtures/seed";
import type { RunEvent } from "@/api/types";

type Listener = (event: RunEvent) => void;

let state: MockState = seedState();
let counter = 0;
const listeners = new Set<Listener>();

export const db = {
  get state(): MockState {
    return state;
  },
  reset() {
    state = seedState();
    counter = 0;
  },
  id(prefix: string): string {
    counter += 1;
    return `${prefix}-${counter}`;
  },
  now(): string {
    return new Date().toISOString();
  },
  subscribe(listener: Listener): () => void {
    listeners.add(listener);
    return () => listeners.delete(listener);
  },
  emit(event: RunEvent) {
    for (const listener of listeners) {
      listener(event);
    }
  },
};

export function apiError(
  status: number,
  code: string,
  message: string,
  fields: Record<string, string> = {},
) {
  return HttpResponse.json({ error: { code, message, fields } }, { status });
}

export const notFound = (what: string) => apiError(404, "not_found", `${what} was not found.`);

export function noContent() {
  return new HttpResponse(null, { status: 204 });
}
