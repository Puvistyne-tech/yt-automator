import { sse } from "msw";
import { db } from "@/api/mocks/db";

export function createEventHandler() {
  return sse("/api/events", ({ client, request }) => {
    const unsubscribe = db.subscribe((event) => client.send({ data: JSON.stringify(event) }));
    request.signal.addEventListener("abort", unsubscribe);
  });
}
