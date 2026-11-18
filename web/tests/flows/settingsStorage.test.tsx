import { screen, within } from "@testing-library/react";
import { db } from "@/api/mocks/db";
import { cancelDialog, findDialog, findToast, findWithin, renderApp } from "../helpers/renderApp";
import { failWith } from "../helpers/server";

const findCard = (title: string) => findWithin(title, "section", { selector: "h2" });

describe("Settings groups", () => {
  it("shows the three groups with help, lock and restart notes", async () => {
    renderApp("/settings");
    await findCard("General");
    await findCard("Storage and cleanup");
    const logging = await findCard("Logging and diagnostics");

    const level = logging.getByLabelText(/^Server log level/);
    expect(level.closest(".field")).toHaveTextContent("Applies after restart");
    const caption = screen.getByLabelText(/^Caption track name/);
    expect(caption).toBeDisabled();
    expect(caption.closest(".field")).toHaveTextContent("AUTOMATOR_YOUTUBE_CAPTION_TRACK_NAME");
    expect(screen.getByLabelText(/^Keep working files/).closest(".field")).toHaveTextContent(
      "videos, thumbnails, captions and metadata stay",
    );
  });

  it("checks new fields before saving and saves them", async () => {
    const { user } = renderApp("/settings");
    const keep = await screen.findByLabelText(/^Keep finished runs/);
    await user.clear(keep);
    await user.type(keep, "-1");
    await user.click(screen.getByRole("button", { name: "Save settings" }));
    expect(screen.getByText("Use a whole number of days, 0 or more.")).toBeInTheDocument();
    expect(keep).toHaveAttribute("aria-invalid", "true");

    await user.clear(keep);
    await user.type(keep, "0");
    await user.selectOptions(screen.getByLabelText(/^Server log level/), "debug");
    await user.click(screen.getByRole("button", { name: "Save settings" }));
    await findToast("Settings saved.");
    expect(db.state.settings).toMatchObject({ keep_runs_days: 0, log_level: "debug" });
  });

  it("keeps automatic cleanup off until it is switched on and saved", async () => {
    const { user } = renderApp("/settings");
    const auto = await screen.findByRole("switch", { name: /^Clean up automatically/ });
    expect(auto).toHaveAttribute("aria-checked", "false");
    expect(auto.closest(".field")).toHaveTextContent("Off until you turn it on.");
    await user.click(auto);
    await user.click(screen.getByRole("button", { name: "Save settings" }));
    await findToast("Settings saved.");
    expect(db.state.settings.auto_cleanup_enabled).toBe(true);
  });

  it("routes a server error to the new field", async () => {
    failWith("put", "/settings", 400, {
      message: "Validation failed",
      fields: { "body.cleanup_interval_hours": "Input should be a valid integer" },
    });
    const { user } = renderApp("/settings");
    const interval = await screen.findByLabelText(/^Automatic cleanup every/);
    await user.clear(interval);
    await user.type(interval, "6");
    await user.click(screen.getByRole("button", { name: "Save settings" }));
    expect(await screen.findByText("Input should be a valid integer")).toBeInTheDocument();
    expect(interval).toHaveAttribute("aria-invalid", "true");
  });
});

describe("Storage and cleanup", () => {
  it("shows disk use per automation", async () => {
    renderApp("/settings");
    const table = await screen.findByRole("table", { name: "Disk use per automation" });
    expect(within(table).getByText("Bedtime stories")).toBeInTheDocument();
    const stat = (label: string) =>
      screen.getByText(label, { selector: ".stat-label" }).closest(".stat-card");
    expect(stat("Free space")).toHaveTextContent("182 GB");
    expect(stat("Working files")).toHaveTextContent("312 MB in stray folders");
  });

  it("copes with no runs and an unreadable disk", async () => {
    db.state.runs = [];
    db.state.storage = { ...db.state.storage, free_bytes: null, disk_bytes: null };
    renderApp("/settings");
    expect(await screen.findByText("No run files yet")).toBeInTheDocument();
    expect(screen.getByText("Unknown")).toBeInTheDocument();
    expect(screen.queryByText("Disk in use")).not.toBeInTheDocument();
  });

  it("previews the cleanup, runs it on confirm and reports what was freed", async () => {
    const { user } = renderApp("/settings");
    await user.click(await screen.findByRole("button", { name: "Clean up now" }));
    const dialog = await findDialog("Clean up storage");
    const preview = await dialog.findByRole("table", { name: "Cleanup preview" });
    expect(within(preview).getByText("Folder run-3f9a2c (no run)")).toBeInTheDocument();
    expect(within(preview).getByText("Remove stray folder")).toBeInTheDocument();
    expect(dialog.getByText(/finished runs older than 30 days go/)).toBeInTheDocument();

    await user.click(dialog.getByRole("button", { name: "Clean up" }));
    await findToast("Cleanup freed 312 MB from 1 item.");
    expect(db.state.storage.strays).toEqual([]);
    expect(screen.queryByRole("dialog", { name: "Clean up storage" })).not.toBeInTheDocument();
  });

  it("removes nothing when the confirmation is cancelled", async () => {
    const { user } = renderApp("/settings");
    await user.click(await screen.findByRole("button", { name: "Clean up now" }));
    await (await findDialog("Clean up storage")).findByRole("table", { name: "Cleanup preview" });
    await cancelDialog(user, "Clean up storage");
    expect(db.state.storage.strays).toHaveLength(1);
  });

  it("says when there is nothing to clean up and offers no confirm", async () => {
    db.state.storage = { ...db.state.storage, strays: [] };
    const { user } = renderApp("/settings");
    await user.click(await screen.findByRole("button", { name: "Clean up now" }));
    const dialog = await findDialog("Clean up storage");
    expect(await dialog.findByText("Nothing to clean up right now.")).toBeInTheDocument();
    expect(dialog.getByRole("button", { name: "Clean up" })).toBeDisabled();
  });

  it("shows a failed cleanup and keeps the files", async () => {
    failWith("post", "/storage/cleanup", 409, { message: "The disk is busy." });
    const { user } = renderApp("/settings");
    await user.click(await screen.findByRole("button", { name: "Clean up now" }));
    const dialog = await findDialog("Clean up storage");
    await dialog.findByRole("table", { name: "Cleanup preview" });
    await user.click(dialog.getByRole("button", { name: "Clean up" }));
    await findToast("The disk is busy.");
    expect(db.state.storage.strays).toHaveLength(1);
  });
});
