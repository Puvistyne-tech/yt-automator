import { screen, within } from "@testing-library/react";
import { startInAllSettings } from "../helpers/editor";
import {
  hidingPipeline,
  openBedtimeWith,
  setBedtimeMusic,
  storedBedtime,
} from "../helpers/hiddenPipeline";
import { findToast } from "../helpers/renderApp";

const musicReset = () =>
  screen.queryByRole("button", { name: "Reset Background music to default" });

type User = Awaited<ReturnType<typeof openBedtimeWith>>["user"];

async function save(user: User) {
  await user.click(screen.getByRole("button", { name: "Save changes" }));
  await findToast(/^Saved/);
}

describe("Automation editor: resets around hidden settings", () => {
  beforeEach(startInAllSettings);

  it("keeps a hidden change out of an optional object's mark and reset", async () => {
    setBedtimeMusic({ volume: 0.8 });
    const { user, content } = await openBedtimeWith(
      hidingPipeline(["music.volume"], { optional: true }),
    );

    expect(content.getByLabelText(/^Play background music/)).toBeInTheDocument();
    expect(musicReset()).not.toBeInTheDocument();
    await user.click(content.getByLabelText(/^Play background music/));
    await user.click(musicReset() as HTMLElement);
    await save(user);

    expect(storedBedtime()?.settings.music).toEqual({ enabled: true, volume: 0.8 });
  });

  it("keeps section counts and resets that leave hidden values alone", async () => {
    setBedtimeMusic({ enabled: false, volume: 0.8 });
    const { user, content } = await openBedtimeWith(hidingPipeline(["music.volume"]));
    const story = within(content.getByRole("region", { name: "Story" }));
    const sound = within(content.getByRole("region", { name: "Sound" }));

    await user.type(story.getByLabelText(/^Series name/), " Plus");
    expect(story.getByText("1 changed")).toBeInTheDocument();
    expect(story.getByRole("button", { name: "Reset Story section to defaults" })).toBeVisible();
    expect(sound.getByText("1 changed")).toBeInTheDocument();
    await user.click(sound.getByRole("button", { name: "Reset Sound section to defaults" }));
    await save(user);

    expect(storedBedtime()?.settings.music).toEqual({ enabled: true, volume: 0.8 });
  });
});
