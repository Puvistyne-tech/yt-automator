import { screen, waitFor } from "@testing-library/react";
import { HttpResponse, http } from "msw";
import { db } from "@/api/mocks/db";
import { findDialog, findRow, findToast, renderApp } from "../helpers/renderApp";
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
    const dialog = await findDialog("Delete automation?");
    await user.click(dialog.getByRole("button", { name: "Cancel" }));
    expect(automation("auto-shorts")).toBeDefined();

    await user.click(row.getByRole("button", { name: "Delete Tamil shorts" }));
    await user.click(
      (await findDialog("Delete automation?")).getByRole("button", { name: "Delete automation" }),
    );

    await findToast(/Deleted “Tamil shorts”/);
    expect(automation("auto-shorts")).toBeUndefined();
    await waitFor(() =>
      expect(screen.queryByRole("link", { name: "Tamil shorts" })).not.toBeInTheDocument(),
    );
  });

  it("queues a run with Run now", async () => {
    const { user } = renderApp("/automations");
    const row = await findRow("Automations", "Tamil shorts");
    const before = db.state.runs.length;

    await user.click(row.getByRole("button", { name: "Run Tamil shorts now" }));

    await findToast("Run queued for Tamil shorts.");
    expect(db.state.runs).toHaveLength(before + 1);
  });
});
