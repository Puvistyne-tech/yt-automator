import { setupWorker } from "msw/browser";
import { completeConnectReturn } from "@/api/mocks/connect";
import { handlers } from "@/api/mocks/handlers";
import { createEventHandler } from "@/api/mocks/handlers/events";
import { startSimulator } from "@/api/mocks/simulator";

export async function startMockApi(): Promise<void> {
  await setupWorker(...handlers, createEventHandler()).start({
    onUnhandledFrame: "bypass",
    quiet: true,
  });
  completeConnectReturn(window.location.search);
  startSimulator();
}
