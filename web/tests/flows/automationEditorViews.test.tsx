import { screen, within } from "@testing-library/react";
import { db } from "@/api/mocks/db";
import { SETTINGS_VIEW_STORAGE_KEY } from "@/features/automation-editor/model/settingsView";
import { findSection, sectionByName, startInAllSettings } from "../helpers/editor";
import { findToast, renderApp } from "../helpers/renderApp";
import { failWith } from "../helpers/server";

const stored = () => db.state.automations.find((a) => a.id === "auto-bedtime");
const viewButton = (name: string) => screen.getByRole("button", { name, pressed: true });

async function openBedtime() {
  const app = renderApp("/automations/auto-bedtime");
  const content = await findSection("Content");
  return { ...app, content };
}

function withMusicVolume(volume: number) {
  const automation = stored();
  if (automation !== undefined) {
    const music = automation.settings.music as Record<string, unknown>;
    automation.settings = { ...automation.settings, music: { ...music, volume } };
  }
}

describe("Automation editor: simple view", () => {
  it("starts in Simple with only the basic settings and main rules", async () => {
    const { content } = await openBedtime();

    expect(viewButton("Simple")).toBeInTheDocument();
    expect(content.getByLabelText(/^Series name/)).toBeInTheDocument();
    expect(content.getByLabelText(/^Play background music/)).toBeInTheDocument();
    expect(content.queryByLabelText(/^Music volume/)).not.toBeInTheDocument();
    expect(content.queryByRole("heading", { name: "Characters" })).not.toBeInTheDocument();
    expect(sectionByName("General").queryByLabelText(/^Description/)).not.toBeInTheDocument();
    expect(sectionByName("Schedule").getByRole("radio", { name: /Every few hours/ })).toBeVisible();
    expect(sectionByName("Schedule").queryByText("When a run fails")).not.toBeInTheDocument();
    expect(screen.getByText(/more options in All settings\.$/)).toBeInTheDocument();
  });

  it("counts hidden changes and remembers the chosen view", async () => {
    withMusicVolume(0.8);
    const { user, unmount } = await openBedtime();

    expect(screen.getByText(/more options in All settings, 1 changed\.$/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Show all settings" }));

    expect(viewButton("All settings")).toBeInTheDocument();
    expect(sectionByName("Content").getByLabelText(/^Music volume/)).toHaveValue("0.8");
    expect(window.localStorage.getItem(SETTINGS_VIEW_STORAGE_KEY)).toBe("all");
    unmount();
    await openBedtime();
    expect(viewButton("All settings")).toBeInTheDocument();
  });

  it("keeps hidden values when saving from Simple", async () => {
    const before = structuredClone(stored());
    const { user, content } = await openBedtime();

    await user.type(content.getByLabelText(/^Series name/), " Plus");
    await user.click(screen.getByRole("button", { name: "Save changes" }));

    await findToast(/^Saved/);
    expect(stored()?.settings.series_name).toBe(`${before?.settings.series_name} Plus`);
    expect(stored()?.settings.music).toEqual(before?.settings.music);
    expect(stored()?.retry_policy).toEqual(before?.retry_policy);
    expect(stored()?.description).toBe(before?.description);
  });

  it("switches to All settings when a hidden setting blocks the save", async () => {
    withMusicVolume(5);
    const { user } = await openBedtime();

    await user.click(screen.getByRole("button", { name: "Save changes" }));

    await findToast("Fix the highlighted fields before saving.");
    expect(viewButton("All settings")).toBeInTheDocument();
    expect(sectionByName("Content").getByText(/must be <= 1/i)).toBeInTheDocument();
  });

  it("switches to All settings when the server rejects a hidden rule", async () => {
    failWith("put", "/automations/:id", 400, {
      code: "validation_failed",
      message: "Validation failed",
      fields: { "retry_policy.retry_delay_minutes": "Too long a wait." },
    });
    const { user, content } = await openBedtime();

    await user.type(content.getByLabelText(/^Series name/), " Plus");
    await user.click(screen.getByRole("button", { name: "Save changes" }));

    expect(await sectionByName("Schedule").findByText("Too long a wait.")).toBeInTheDocument();
    expect(viewButton("All settings")).toBeInTheDocument();
  });

  it("stays in Simple when the error is on a visible field", async () => {
    const { user } = await openBedtime();

    await user.clear(sectionByName("General").getByLabelText(/^Name/));
    await user.click(screen.getByRole("button", { name: "Save changes" }));

    await findToast("Fix the highlighted fields before saving.");
    expect(viewButton("Simple")).toBeInTheDocument();
  });
});

describe("Automation editor: all settings filters", () => {
  beforeEach(startInAllSettings);

  it("searches settings by title and description and shows an empty state", async () => {
    const { user, content } = await openBedtime();
    const search = content.getByRole("searchbox", { name: "Search settings" });

    await user.type(search, "volume");
    expect(content.getByLabelText(/^Music volume/)).toBeInTheDocument();
    expect(content.queryByLabelText(/^Series name/)).not.toBeInTheDocument();
    expect(content.queryByRole("heading", { name: "Story" })).not.toBeInTheDocument();

    await user.clear(search);
    await user.type(search, "one theme from this list");
    expect(content.getByRole("heading", { name: "Story" })).toBeInTheDocument();
    expect(content.getByText("Moral themes")).toBeInTheDocument();
    expect(content.queryByRole("heading", { name: "Characters" })).not.toBeInTheDocument();

    await user.type(search, " zebra");
    expect(content.getByText("No settings match")).toBeInTheDocument();
    await user.click(content.getByRole("button", { name: "Clear search" }));
    expect(search).toHaveValue("");
    expect(content.getByLabelText(/^Series name/)).toBeInTheDocument();
  });

  it("shows only changed settings with Changed only", async () => {
    withMusicVolume(0.8);
    const { user, content } = await openBedtime();

    await user.click(content.getByRole("switch", { name: "Changed only" }));

    const sound = within(content.getByRole("region", { name: "Sound" }));
    expect(sound.getByLabelText(/^Music volume/)).toBeInTheDocument();
    expect(sound.queryByLabelText(/^Play background music/)).not.toBeInTheDocument();
    expect(content.queryByLabelText(/^Series name/)).not.toBeInTheDocument();
  });
});
