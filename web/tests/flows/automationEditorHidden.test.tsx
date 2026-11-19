import { screen } from "@testing-library/react";
import { HttpResponse, http } from "msw";
import { db } from "@/api/mocks/db";
import { kidsStoryPipeline } from "@/api/mocks/fixtures/pipeline";
import { findSection } from "../helpers/editor";
import { findToast, renderApp } from "../helpers/renderApp";
import { server } from "../helpers/server";

const stored = () => db.state.automations.find((a) => a.id === "auto-bedtime");
const hiding = {
  ...kidsStoryPipeline,
  ui_schema: { ...kidsStoryPipeline.ui_schema, "ui:hidden": ["music.volume"] },
};

function setVolume(volume: number) {
  const automation = stored();
  if (automation !== undefined) {
    const music = automation.settings.music as Record<string, unknown>;
    automation.settings = { ...automation.settings, music: { ...music, volume } };
  }
}

async function openBedtime() {
  server.use(
    http.get("/api/pipelines", () => HttpResponse.json([hiding])),
    http.get("/api/pipelines/:typeId", () => HttpResponse.json(hiding)),
  );
  const app = renderApp("/automations/auto-bedtime");
  const content = await findSection("Content");
  return { ...app, content };
}

describe("Automation editor: hidden settings", () => {
  it("never shows or counts a hidden setting and keeps its value on save", async () => {
    setVolume(0.8);
    const before = structuredClone(stored()?.settings.music);
    const { user, content } = await openBedtime();

    expect(screen.getByText(/more options in All settings\.$/)).toBeInTheDocument();
    expect(content.getByLabelText(/^Play background music/)).toBeInTheDocument();
    expect(content.queryByLabelText(/^Music volume/)).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Show all settings" }));
    expect(content.getByLabelText(/^Series name/)).toBeInTheDocument();
    expect(content.queryByLabelText(/^Music volume/)).not.toBeInTheDocument();
    await user.type(content.getByRole("searchbox", { name: "Search settings" }), "volume");
    expect(content.getByText("No settings match")).toBeInTheDocument();

    await user.click(content.getByRole("button", { name: "Clear search" }));
    await user.type(content.getByLabelText(/^Series name/), " Plus");
    await user.click(screen.getByRole("button", { name: "Save changes" }));

    await findToast(/^Saved/);
    expect(stored()?.settings.music).toEqual(before);
  });

  it("shows a hidden setting that blocks the save", async () => {
    setVolume(5);
    const { user, content } = await openBedtime();

    await user.click(screen.getByRole("button", { name: "Save changes" }));

    await findToast("Fix the highlighted fields before saving.");
    expect(content.getByLabelText(/^Music volume/)).toBeInTheDocument();
    expect(content.getByText(/must be <= 1/i)).toBeInTheDocument();
  });
});
