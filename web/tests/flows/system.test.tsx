import { screen, within } from "@testing-library/react";
import { db } from "@/api/mocks/db";
import { findToast, findWithin, renderApp } from "../helpers/renderApp";
import { failWith } from "../helpers/server";

const findCard = (title: string) => findWithin(title, "section", { selector: "h2" });

describe("Settings page", () => {
  it("validates and saves app settings", async () => {
    const { user } = renderApp("/settings");
    const parallel = await screen.findByLabelText(/^Parallel runs/);
    expect(
      screen.getByDisplayValue("~/Library/Application Support/YouTube Automator"),
    ).toHaveAttribute("readonly");

    await user.clear(parallel);
    await user.click(screen.getByRole("button", { name: "Save settings" }));
    expect(screen.getByText("Use a whole number, at least 1.")).toBeInTheDocument();

    await user.type(parallel, "3");
    await user.selectOptions(screen.getByLabelText(/^Timezone/), "UTC");
    await user.click(screen.getByRole("button", { name: "Save settings" }));

    await findToast("Settings saved.");
    expect(db.state.settings).toMatchObject({ max_parallel_runs: 3, timezone: "UTC" });
  });

  it("shows server field errors on the matching setting", async () => {
    failWith("put", "/settings", 400, {
      message: "The settings are not valid.",
      fields: { "body.timezone": "Unknown timezone." },
    });
    const { user } = renderApp("/settings");
    await user.selectOptions(await screen.findByLabelText(/^Timezone/), "UTC");
    await user.click(screen.getByRole("button", { name: "Save settings" }));

    await findToast("The settings are not valid.");
    expect(screen.getByText("Unknown timezone.")).toBeInTheDocument();
    expect(screen.getByLabelText(/^Timezone/)).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByText("Unsaved changes")).toBeInTheDocument();
  });
});

describe("Dashboard", () => {
  it("summarizes automations, review queue, recent runs and quota", async () => {
    renderApp("/");

    const review = await findCard("Waiting for your review");
    expect(await review.findByText("Bedtime stories")).toBeInTheDocument();
    const recent = await screen.findByRole("table", { name: "Recent runs" });
    expect(within(recent).getAllByRole("row")).toHaveLength(7);
    const quota = await findCard("YouTube quota today");
    expect(quota.getByText("Main Google project")).toBeInTheDocument();
    expect(
      screen.getByText("Awaiting review", { selector: ".stat-label" }).closest(".stat-card"),
    ).toHaveTextContent("1");
  });

  it("shows an all caught up state with nothing to review", async () => {
    db.state.runs = db.state.runs.filter((r) => r.status !== "awaiting_review");
    renderApp("/");

    expect(await screen.findByText("All caught up")).toBeInTheDocument();
  });
});
