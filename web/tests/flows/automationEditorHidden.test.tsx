import { screen } from "@testing-library/react";
import {
  hidingPipeline,
  openBedtimeWith,
  setBedtimeMusic,
  storedBedtime,
} from "../helpers/hiddenPipeline";
import { findToast } from "../helpers/renderApp";
import { failWith } from "../helpers/server";

const hidingVolume = () => openBedtimeWith(hidingPipeline(["music.volume"]));

describe("Automation editor: hidden settings", () => {
  it("never shows or counts a hidden setting and keeps its value on save", async () => {
    setBedtimeMusic({ volume: 0.8 });
    const before = structuredClone(storedBedtime()?.settings.music);
    const { user, content } = await hidingVolume();

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
    expect(storedBedtime()?.settings.music).toEqual(before);
  });

  it("finds nothing with Changed only when the only change is hidden", async () => {
    setBedtimeMusic({ volume: 0.8 });
    const { user, content } = await hidingVolume();

    await user.click(screen.getByRole("button", { name: "Show all settings" }));
    await user.click(content.getByRole("switch", { name: "Changed only" }));

    expect(content.getByText("No settings match")).toBeInTheDocument();
  });

  it("shows a hidden setting that blocks the save", async () => {
    setBedtimeMusic({ volume: 5 });
    const { user, content } = await hidingVolume();

    await user.click(screen.getByRole("button", { name: "Save changes" }));

    await findToast("Fix the highlighted fields before saving.");
    expect(content.getByLabelText(/^Music volume/)).toBeInTheDocument();
    expect(content.getByText(/must be <= 1/i)).toBeInTheDocument();
  });

  it("shows a hidden setting the server rejects with its message", async () => {
    failWith("put", "/automations/:id", 400, {
      code: "validation_failed",
      message: "Validation failed",
      fields: { "settings.music.volume": "Too loud for bedtime." },
    });
    const { user, content } = await hidingVolume();

    await user.type(content.getByLabelText(/^Series name/), " Plus");
    await user.click(screen.getByRole("button", { name: "Save changes" }));

    expect(await content.findByText("Too loud for bedtime.")).toBeInTheDocument();
    expect(content.getByLabelText(/^Music volume/)).toBeInTheDocument();
  });
});
