import { screen, waitFor } from "@testing-library/react";
import { db } from "@/api/mocks/db";
import { findSection } from "../helpers/editor";
import { findToast, pathOf, renderApp } from "../helpers/renderApp";
import { failWith } from "../helpers/server";

async function openEditor(id: string) {
  const app = renderApp(`/automations/${id}`);
  const general = await findSection("General");
  return { ...app, general };
}

describe("Automation editor: Run now", () => {
  it("queues a run of the saved automation and links the toast to it", async () => {
    const { user, router } = await openEditor("auto-shorts");
    const known = db.state.runs.map((r) => r.id);

    await user.click(screen.getByRole("button", { name: "Run now" }));

    await findToast("Run queued for Tamil shorts.");
    const queued = db.state.runs.find((r) => !known.includes(r.id));
    expect(queued?.automation_id).toBe("auto-shorts");
    await user.click(screen.getByRole("button", { name: "View run" }));
    await waitFor(() => expect(pathOf(router)).toBe(`/runs/${queued?.id}`));
  });

  it("disables Run now with a reason while there are unsaved changes", async () => {
    const { user, general } = await openEditor("auto-shorts");

    await user.type(general.getByLabelText(/^Name/), " extra");

    const button = screen.getByRole("button", { name: "Run now" });
    expect(button).toBeDisabled();
    expect(button).toHaveAccessibleDescription(
      "Save your changes first: a run uses the saved settings.",
    );
  });

  it("does not offer Run now before the automation exists", async () => {
    renderApp("/automations/new");
    await findSection("General");

    expect(screen.queryByRole("button", { name: "Run now" })).not.toBeInTheDocument();
  });

  it("reports a failed Run now", async () => {
    failWith("post", "/automations/:id/runs", 409, { message: "Pipeline is not installed." });
    const { user } = await openEditor("auto-shorts");
    const before = db.state.runs.length;

    await user.click(screen.getByRole("button", { name: "Run now" }));

    await findToast("Pipeline is not installed.");
    expect(db.state.runs).toHaveLength(before);
  });

  it("words the enabled switch for a manual schedule", async () => {
    const { general } = await openEditor("auto-festival");

    expect(
      general.getByRole("switch", {
        name: "Enabled (manual schedule: runs only start from Run now)",
      }),
    ).toBeInTheDocument();
  });
});

describe("Missing automations", () => {
  it("shows a retryable error state when the automation fails to load", async () => {
    failWith("get", "/automations/:id", 500, { message: "Database is locked." });
    renderApp("/automations/auto-bedtime");

    expect(await screen.findByText("Database is locked.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
  });

  it("shows a not-found state with a way back instead of a retry", async () => {
    const { user, router } = renderApp("/automations/gone");

    expect(await screen.findByText("Automation not found")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Try again" })).not.toBeInTheDocument();
    await user.click(screen.getByRole("link", { name: "Back to automations" }));
    await waitFor(() => expect(pathOf(router)).toBe("/automations"));
  });

  it("marks a kept run's automation as deleted instead of linking to it", async () => {
    db.state.automations = db.state.automations.filter((a) => a.id !== "auto-bedtime");
    renderApp("/runs/run-review");
    await screen.findByRole("heading", { level: 1 });

    expect(await screen.findByText("Automation deleted")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Open automation" })).not.toBeInTheDocument();
  });

  it("links a run to its automation while it exists", async () => {
    renderApp("/runs/run-review");

    expect(await screen.findByRole("link", { name: "Open automation" })).toHaveAttribute(
      "href",
      "/automations/auto-bedtime",
    );
  });
});
