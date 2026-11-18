import { screen, waitFor } from "@testing-library/react";
import { db } from "@/api/mocks/db";
import { findSection, sectionByName } from "../helpers/editor";
import { pathOf, renderApp } from "../helpers/renderApp";
import { failWith, server } from "../helpers/server";

async function openEditor(id: string) {
  const app = renderApp(`/automations/${id}`);
  const general = await findSection("General");
  return { ...app, general };
}

describe("Automation editor: Run now", () => {
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

  it("words the enabled switch after the schedule kind", async () => {
    const { user, general } = await openEditor("auto-festival");
    expect(
      general.getByRole("switch", {
        name: "Enabled (manual schedule: runs only start from Run now)",
      }),
    ).toBeInTheDocument();

    await user.click(sectionByName("Schedule").getByRole("radio", { name: /Cron expression/ }));

    expect(general.getByRole("switch", { name: "Enabled: run on schedule" })).toBeInTheDocument();
  });
});

describe("Missing automations", () => {
  it("shows a retryable error state when the automation fails to load", async () => {
    failWith("get", "/automations/:id", 500, { message: "Database is locked." });
    const { user } = renderApp("/automations/auto-bedtime");
    expect(await screen.findByText("Database is locked.")).toBeInTheDocument();

    server.resetHandlers();
    await user.click(screen.getByRole("button", { name: "Try again" }));

    expect(await findSection("General")).toBeTruthy();
    expect(screen.queryByText("Database is locked.")).not.toBeInTheDocument();
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
