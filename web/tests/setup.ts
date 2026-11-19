import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { db } from "@/api/mocks/db";
import { server } from "./helpers/server";

beforeAll(() => server.listen({ onUnhandledFrame: "error" }));

beforeEach(() => db.reset());

afterEach(() => {
  cleanup();
  server.resetHandlers();
  db.reset();
  window.localStorage.clear();
});

afterAll(() => server.close());
