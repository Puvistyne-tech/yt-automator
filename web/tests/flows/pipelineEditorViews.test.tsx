import { screen } from "@testing-library/react";
import { SETTINGS_VIEW_STORAGE_KEY } from "@/shared/settings-view/settingsView";
import { startInAllSettings } from "../helpers/editor";
import { renderApp } from "../helpers/renderApp";
import { failWith } from "../helpers/server";
import { startNewPipeline } from "../helpers/templates";

const pressed = (name: string) => screen.getByRole("button", { name, pressed: true });
const sectionTitle = (name: string) => screen.queryByRole("heading", { name });

function expectSimple() {
  expect(pressed("Simple")).toBeInTheDocument();
  expect(screen.getByLabelText(/^What the videos are about/)).toBeInTheDocument();
  expect(sectionTitle("Look and sound")).toBeInTheDocument();
  expect(screen.queryByLabelText(/^Music mood/)).not.toBeInTheDocument();
  expect(sectionTitle("Publishing")).not.toBeInTheDocument();
  expect(screen.getByText(/more options in All settings\.$/)).toBeInTheDocument();
}

describe("Pipeline editor: settings views", () => {
  it("opens a new pipeline in Simple even when All settings is remembered", async () => {
    startInAllSettings();
    const { user } = await startNewPipeline("General audience");

    expectSimple();
    expect(window.localStorage.getItem(SETTINGS_VIEW_STORAGE_KEY)).toBe("all");
    await user.click(screen.getByRole("button", { name: "All settings" }));
    expect(pressed("All settings")).toBeInTheDocument();
  });

  it("shows every section in All settings, searches them and remembers the view", async () => {
    const { user, unmount } = renderApp("/pipelines/space-facts");
    await screen.findByLabelText(/^Name/);
    expectSimple();

    await user.click(screen.getByRole("button", { name: "Show all settings" }));
    expect(screen.getByLabelText(/^Music mood/)).toBeInTheDocument();
    expect(sectionTitle("Publishing")).toBeInTheDocument();
    expect(screen.queryByRole("switch", { name: "Changed only" })).not.toBeInTheDocument();

    await user.type(screen.getByRole("searchbox", { name: "Search settings" }), "zebra");
    expect(screen.getByText("No settings match")).toBeInTheDocument();
    expect(screen.getByText("Try another word.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Clear search" }));
    expect(screen.getByLabelText(/^Music mood/)).toBeInTheDocument();

    unmount();
    renderApp("/pipelines/space-facts");
    await screen.findByLabelText(/^Name/);
    expect(pressed("All settings")).toBeInTheDocument();
  });

  it("switches to All settings when a save fails on a field Simple hides", async () => {
    failWith("put", "/templates/:id", 400, {
      message: "Validation failed",
      fields: { "definition.music_mood": "Pick a calmer mood." },
    });
    const { user } = renderApp("/pipelines/space-facts");
    await screen.findByLabelText(/^Name/);

    await user.click(screen.getByRole("button", { name: "Save changes" }));

    expect(await screen.findByLabelText(/^Music mood/)).toHaveAccessibleDescription(
      /Pick a calmer mood/,
    );
    expect(pressed("All settings")).toBeInTheDocument();

    await user.type(screen.getByRole("searchbox", { name: "Search settings" }), "zebra");
    expect(screen.getByLabelText(/^Music mood/)).toBeInTheDocument();
    expect(screen.queryByLabelText(/^Tone/)).not.toBeInTheDocument();
    expect(screen.queryByText("No settings match")).not.toBeInTheDocument();
  });

  it("keeps only the settings a search matches", async () => {
    startInAllSettings();
    const { user } = renderApp("/pipelines/space-facts");
    await screen.findByLabelText(/^Name/);

    await user.type(screen.getByRole("searchbox", { name: "Search settings" }), "music");

    expect(screen.getByLabelText(/^Music mood/)).toBeInTheDocument();
    expect(screen.queryByLabelText(/^Tone/)).not.toBeInTheDocument();
    expect(sectionTitle("Publishing")).not.toBeInTheDocument();
    expect(screen.getByLabelText(/^Name/)).toBeInTheDocument();
  });

  it("offers both views on a built-in pipeline", async () => {
    const { user } = renderApp("/pipelines/kids_story");
    await screen.findByText(/Built-in pipelines cannot be changed/);
    expectSimple();

    await user.click(screen.getByRole("button", { name: "All settings" }));
    expect(screen.getByLabelText(/^Music mood/)).toBeDisabled();
  });
});
