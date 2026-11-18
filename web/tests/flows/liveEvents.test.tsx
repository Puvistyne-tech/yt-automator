import { act, screen, waitFor, within } from "@testing-library/react";
import { keys } from "@/api/keys";
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

  it("shows stored logs and appends live ones with their stage and level", async () => {
    const { user } = renderApp("/runs/run-live");
    await screen.findByRole("heading", { level: 1 });
    act(() => latest().onopen?.());
    await user.click(screen.getByRole("tab", { name: "Logs" }));
    const log = screen.getByRole("log", { name: "Run log" });
    expect(within(log).getByText("Story written in English and Tamil")).toBeInTheDocument();

    latest().emit(
      event("log", { message: "Scene 3 looks dark", level: "warning", stage_id: "images" }),
    );
    const line = (await screen.findByText("Scene 3 looks dark")).closest(".log-line");
    expect(line).toHaveAttribute("data-level", "warning");
    expect(line).toHaveTextContent("Illustrate scenes");
  });

  it("applies status events to the open run", async () => {
    renderApp("/runs/run-live");
    await screen.findByRole("heading", { level: 1 });
    act(() => latest().onopen?.());

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

  it("refreshes runs and shows live again once the stream reopens", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const { client } = renderApp("/");
    act(() => latest().onerror?.());
    act(() => vi.advanceTimersByTime(1000));
    await waitFor(() => expect(FakeEventSource.instances).toHaveLength(2));
    const invalidate = vi.spyOn(client, "invalidateQueries");

    act(() => latest().onopen?.());

    expect(await screen.findByText("Live updates on")).toBeInTheDocument();
    expect(invalidate).toHaveBeenCalledWith({ queryKey: keys.runs });
  });

  it("does not refresh runs on the first open", async () => {
    const { client } = renderApp("/");
    const invalidate = vi.spyOn(client, "invalidateQueries");

    act(() => latest().onopen?.());

    expect(await screen.findByText("Live updates on")).toBeInTheDocument();
    expect(invalidate).not.toHaveBeenCalledWith({ queryKey: keys.runs });
  });

  it("closes the stream when the app unmounts", () => {
    const { unmount } = renderApp("/");
    const source = latest();

    unmount();

    expect(source.closed).toBe(true);
  });

  it("reports when the browser has no event stream support", async () => {
    vi.stubGlobal("EventSource", undefined);
    renderApp("/");

    expect(await screen.findByText("Live updates unavailable")).toBeInTheDocument();
    expect(FakeEventSource.instances).toHaveLength(0);
  });
});
