import { screen, waitFor } from "@testing-library/react";
import { HttpResponse, http } from "msw";
import { db } from "@/api/mocks/db";
import {
  cancelDialog,
  confirmDialog,
  findRow,
  findToast,
  pathOf,
  renderApp,
} from "../helpers/renderApp";
import { failWith, server } from "../helpers/server";

const automation = (id: string) => db.state.automations.find((a) => a.id === id);

describe("Automations list", () => {
  it("lists every automation with its pipeline, languages, targets and schedule", async () => {
    renderApp("/automations");

    const row = await findRow("Automations", "Bedtime stories");
    expect(row.getByText("Kutty Stories", { selector: "td span" })).toBeInTheDocument();
    expect(row.getByText("English, Tamil")).toBeInTheDocument();
    expect(row.getByText("Kutty Stories, Kutty Kathaigal")).toBeInTheDocument();
    expect(row.getByText("Every day at 18:00 (Asia/Kolkata)")).toBeInTheDocument();
    expect(row.getByText("Awaiting review")).toBeInTheDocument();
    const shorts = await findRow("Automations", "Tamil shorts");
    expect(shorts.getByText("Every 6 hours")).toBeInTheDocument();
    const festival = await findRow("Automations", "Festival specials");
    expect(festival.getByText("Paused")).toBeInTheDocument();
    expect(
      festival.getByRole("link", { name: "Reconnect Kutty Classics to keep publishing." }),
    ).toHaveAttribute("href", "/channels");
    expect(row.queryByText(/to keep publishing/)).not.toBeInTheDocument();
  });

  it("shows an empty state with a call to action when there are none", async () => {
    server.use(http.get("/api/automations", () => HttpResponse.json([])));
    renderApp("/automations");

    expect(await screen.findByText("No automations yet")).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: /Create automation/ })).not.toHaveLength(0);
  });

  it("shows an error state when the list cannot load", async () => {
    failWith("get", "/automations", 500, { message: "Database is locked." });
    renderApp("/automations");

    expect(await screen.findByText("Database is locked.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
  });

  it("toggles enabled optimistically and saves it", async () => {
    const { user } = renderApp("/automations");
    const row = await findRow("Automations", "Festival specials");
    const toggle = row.getByRole("switch", { name: "Enable Festival specials" });

    await user.click(toggle);

    expect(toggle).toHaveAttribute("aria-checked", "true");
    await findToast("Festival specials enabled.");
    expect(automation("auto-festival")?.enabled).toBe(true);
  });

  it("rolls the switch back when saving fails", async () => {
    failWith("patch", "/automations/:id", 409, { message: "Cannot enable right now." });
    const { user } = renderApp("/automations");
    const row = await findRow("Automations", "Festival specials");
    const toggle = row.getByRole("switch", { name: "Enable Festival specials" });

    await user.click(toggle);

    await findToast("Cannot enable right now.");
    await waitFor(() => expect(toggle).toHaveAttribute("aria-checked", "false"));
  });

  it("duplicates an automation", async () => {
    const { user } = renderApp("/automations");
    const row = await findRow("Automations", "Bedtime stories");

    await user.click(row.getByRole("button", { name: "Duplicate Bedtime stories" }));

    await findToast("Created “Bedtime stories (copy)”.");
    expect(await screen.findByRole("link", { name: "Bedtime stories (copy)" })).toBeInTheDocument();
  });

  it("deletes only after confirmation", async () => {
    const { user } = renderApp("/automations");
    const row = await findRow("Automations", "Tamil shorts");

    await user.click(row.getByRole("button", { name: "Delete Tamil shorts" }));
    await cancelDialog(user, "Delete automation?");
    expect(automation("auto-shorts")).toBeDefined();

    await user.click(row.getByRole("button", { name: "Delete Tamil shorts" }));
    await confirmDialog(user, "Delete automation?", "Delete automation");

    await findToast(/Deleted “Tamil shorts”/);
    expect(automation("auto-shorts")).toBeUndefined();
    await waitFor(() =>
      expect(screen.queryByRole("link", { name: "Tamil shorts" })).not.toBeInTheDocument(),
    );
  });

  it("queues a run with Run now and links the toast to the new run", async () => {
    const { user, router } = renderApp("/automations");
    const row = await findRow("Automations", "Tamil shorts");
    const known = db.state.runs.map((r) => r.id);

    await user.click(row.getByRole("button", { name: "Run Tamil shorts now" }));

    await findToast("Run queued for Tamil shorts.");
    expect(db.state.runs).toHaveLength(known.length + 1);
    const queued = db.state.runs.find((r) => !known.includes(r.id));
    await user.click(screen.getByRole("button", { name: "View run" }));
    await waitFor(() => expect(pathOf(router)).toBe(`/runs/${queued?.id}`));
  });

  it("reports a failed duplicate without adding a row", async () => {
    failWith("post", "/automations/:id/duplicate", 500, { message: "Could not copy." });
    const { user } = renderApp("/automations");
    const row = await findRow("Automations", "Bedtime stories");

    await user.click(row.getByRole("button", { name: "Duplicate Bedtime stories" }));

    await findToast("Could not copy.");
    expect(screen.queryByRole("link", { name: "Bedtime stories (copy)" })).not.toBeInTheDocument();
  });

  it("closes the delete dialog and keeps the row when deleting fails", async () => {
    failWith("delete", "/automations/:id", 409, { message: "A run is still publishing." });
    const { user } = renderApp("/automations");
    const row = await findRow("Automations", "Tamil shorts");

    await user.click(row.getByRole("button", { name: "Delete Tamil shorts" }));
    await confirmDialog(user, "Delete automation?", "Delete automation");

    await findToast("A run is still publishing.");
    await waitFor(() =>
      expect(screen.queryByRole("dialog", { name: "Delete automation?" })).not.toBeInTheDocument(),
    );
    expect(screen.getByRole("link", { name: "Tamil shorts" })).toBeInTheDocument();
  });

  it("reports a failed Run now", async () => {
    failWith("post", "/automations/:id/runs", 409, { message: "Automation has no languages." });
    const { user } = renderApp("/automations");
    const row = await findRow("Automations", "Tamil shorts");
    const before = db.state.runs.length;

    await user.click(row.getByRole("button", { name: "Run Tamil shorts now" }));

    await findToast("Automation has no languages.");
    expect(db.state.runs).toHaveLength(before);
  });
});
