import { act, screen, waitFor } from "@testing-library/react";
import { db } from "@/api/mocks/db";
import type { JsonObject, RunEvent } from "@/api/types";
import { renderApp } from "../helpers/renderApp";

class FakeEventSource {
  static instances: FakeEventSource[] = [];
  readonly url: string;
  onopen: (() => void) | null = null;
  onmessage: ((message: MessageEvent<string>) => void) | null = null;
  onerror: (() => void) | null = null;
  closed = false;

  constructor(url: string) {
    this.url = url;
    FakeEventSource.instances.push(this);
  }

  close() {
    this.closed = true;
  }

  emit(event: RunEvent) {
    act(() => this.onmessage?.(new MessageEvent("message", { data: JSON.stringify(event) })));
  }
}

const latest = () => {
  const source = FakeEventSource.instances.at(-1);
  if (source === undefined) {
    throw new Error("No event source opened");
  }
  return source;
};

const event = (kind: RunEvent["kind"], payload: JsonObject): RunEvent => ({
  run_id: "run-live",
  kind,
  at: new Date().toISOString(),
  payload,
});

beforeEach(() => {
  FakeEventSource.instances = [];
  vi.stubGlobal("EventSource", FakeEventSource);
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe("Live run events", () => {
  it("opens the event stream and shows when it is live", async () => {
    renderApp("/");

    expect(latest().url).toMatch(/\/api\/events$/);
    expect(screen.getByText("Connecting…")).toBeInTheDocument();
    act(() => latest().onopen?.());
    expect(await screen.findByText("Live updates on")).toBeInTheDocument();
  });

  it("applies status and log events to the open run", async () => {
    const { user } = renderApp("/runs/run-live");
    await screen.findByRole("heading", { level: 1 });
    act(() => latest().onopen?.());

    latest().emit(
      event("log", { message: "Painting scene 3 of 8", level: "info", stage_id: "visuals" }),
    );
    await user.click(screen.getByRole("tab", { name: "Logs" }));
    expect(screen.getByText("Painting scene 3 of 8")).toBeInTheDocument();

    db.state.runs = db.state.runs.map((r) =>
      r.id === "run-live" ? { ...r, status: "failed" } : r,
    );
    latest().emit(event("status", { status: "failed", error: "Out of memory." }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Out of memory.");
  });

  it("reconnects with backoff after an error", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    renderApp("/");
    const first = latest();

    act(() => first.onerror?.());
    expect(first.closed).toBe(true);
    expect(await screen.findByText("Reconnecting…")).toBeInTheDocument();
    act(() => vi.advanceTimersByTime(1000));

    await waitFor(() => expect(FakeEventSource.instances).toHaveLength(2));
  });
});
