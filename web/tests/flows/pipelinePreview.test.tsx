import { screen, within } from "@testing-library/react";
import { delay, http } from "msw";
import { db } from "@/api/mocks/db";
import {
  clickWrite,
  newExplainer,
  openSaved,
  PREVIEW,
  previewCard,
  SAMPLE,
  writeSample,
} from "../helpers/preview";
import { recordBodies, server } from "../helpers/server";

describe("Pipeline editor: sample script", () => {
  it.each([
    {
      name: "a general explainer on a new pipeline",
      open: newExplainer,
      title: "Understanding tides",
      headings: ["What it is", "Why it happens", "A closer look", "Why it matters"],
      takeaway: "Behind tides are a few simple forces working together.",
    },
    {
      name: "a kids story on the read-only built-in",
      open: () => openSaved("/pipelines/kids_story"),
      title: "The little lantern and tides",
      headings: [],
      takeaway: "Curious questions lead to kind discoveries.",
    },
  ])("shows $name in scene order with its upload text", async (example) => {
    const { user } = await example.open();
    expect(previewCard().getByText(/only the script/)).toBeInTheDocument();

    const sample = await writeSample(user, "tides");

    expect(sample.getByRole("heading", { name: example.title })).toBeInTheDocument();
    const scenes = within(sample.getByRole("list", { name: "Scenes" })).getAllByRole("listitem");
    expect(scenes).toHaveLength(4);
    expect(scenes[0]).toHaveTextContent("A slow pan across the opening picture");
    const headings = scenes.flatMap((scene) => within(scene).queryAllByRole("heading"));
    expect(headings.map((heading) => heading.textContent)).toEqual(example.headings);
    expect(sample.getByText(example.takeaway, { selector: "p" })).toBeInTheDocument();
    expect(sample.getByText("YouTube title").nextSibling).toHaveTextContent(example.title);
    expect(sample.getByText(/Written by ollama/)).toBeInTheDocument();
  });

  it("replaces the shown sample with the next one", async () => {
    const { user } = await openSaved("/pipelines/space-facts");
    await writeSample(user, "tides");

    await writeSample(user, "stars");

    expect(await screen.findByRole("heading", { name: /and stars$/ })).toBeInTheDocument();
    expect(screen.getAllByRole("article", SAMPLE)).toHaveLength(1);
    expect(screen.queryByRole("heading", { name: /and tides$/ })).not.toBeInTheDocument();
  });

  it("offers the engine's languages with the first chosen", async () => {
    await openSaved("/pipelines/space-facts");
    const language = previewCard().getByLabelText("Language");

    const options = await within(language).findAllByRole("option");
    expect(options.map((option) => option.textContent)).toEqual(["English", "Tamil"]);
    expect(language).toHaveDisplayValue("English");
  });

  it("sends the unsaved form values in the chosen language and saves nothing", async () => {
    const bodies = recordBodies("post", PREVIEW);
    const before = structuredClone(db.state.templates);
    const { user } = await openSaved("/pipelines/space-facts");
    await user.type(screen.getByLabelText(/^Name/), " daily");
    await user.selectOptions(previewCard().getByLabelText("Language"), "ta");

    await writeSample(user);

    expect(bodies).toEqual([
      expect.objectContaining({
        name: "Space facts daily",
        engine: "narrated_video",
        audience: "general",
        language: "ta",
        topic: "",
        definition: expect.objectContaining(before[0]?.definition),
      }),
    ]);
    expect(db.state.templates).toEqual(before);
    expect(screen.getByText("Unsaved changes")).toBeInTheDocument();
  });

  it("shows progress and sends one request however often the button is pressed", async () => {
    server.use(http.post(`/api${PREVIEW}`, () => delay("infinite")));
    const bodies = recordBodies("post", PREVIEW);
    const { user } = await openSaved("/pipelines/space-facts");

    await clickWrite(user);
    await user.click(previewCard().getByRole("button", { name: /Writing/ }));

    expect(
      await previewCard().findByRole("status", { name: /Writing a sample script/ }),
    ).toBeVisible();
    expect(previewCard().getByRole("button", { name: /Writing/ })).toBeDisabled();
    expect(bodies).toHaveLength(1);
  });
});
