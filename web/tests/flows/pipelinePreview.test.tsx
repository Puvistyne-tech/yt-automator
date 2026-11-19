import { screen, within } from "@testing-library/react";
import { delay, http } from "msw";
import { db } from "@/api/mocks/db";
import { renderApp, type User } from "../helpers/renderApp";
import { failWith, recordBodies, server } from "../helpers/server";
import { startNewPipeline } from "../helpers/templates";

const PREVIEW = "/templates/preview-script";
const WRITE = { name: "Write a sample script" };

function previewCard() {
  return within(screen.getByRole("region", { name: "Try a sample script" }));
}

async function openSaved(route: string) {
  const app = renderApp(route);
  await screen.findByRole("region", { name: "Try a sample script" });
  return app;
}

async function newExplainer() {
  const app = await startNewPipeline("General audience");
  await app.user.type(screen.getByLabelText(/^Name/), "Sky facts");
  await app.user.selectOptions(screen.getByRole("combobox", { name: "Format" }), "explainer");
  return app;
}

async function writeSample(user: User, topic = "") {
  const card = previewCard();
  if (topic !== "") {
    await user.type(card.getByLabelText(/^Topic/), topic);
  }
  await user.click(card.getByRole("button", WRITE));
  return within(await screen.findByRole("article", { name: /^Sample script/ }));
}

function disableWriters() {
  db.state.providerConfig = db.state.providerConfig.map((config) => ({
    ...config,
    chain: config.chain.map((choice) => ({ ...choice, enabled: false })),
  }));
}

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

  it("disables the button and shows progress while writing", async () => {
    server.use(http.post(`/api${PREVIEW}`, () => delay("infinite")));
    const { user } = await openSaved("/pipelines/space-facts");

    await user.click(previewCard().getByRole("button", WRITE));

    expect(
      await previewCard().findByRole("status", { name: /Writing a sample script/ }),
    ).toBeVisible();
    expect(previewCard().getByRole("button", { name: /Writing/ })).toBeDisabled();
  });

  it("shows refused values at their fields", async () => {
    failWith("post", PREVIEW, 400, {
      code: "validation_failed",
      message: "Validation failed",
      fields: {
        topic: "String should have at most 300 characters",
        "definition.brief": "The brief speaks to children.",
      },
    });
    const { user } = await openSaved("/pipelines/space-facts");

    await user.click(previewCard().getByRole("button", WRITE));

    expect(await previewCard().findByLabelText(/^Topic/)).toHaveAccessibleDescription(
      /at most 300 characters/,
    );
    expect(screen.getByLabelText(/^What the videos are about/)).toHaveAccessibleDescription(
      /The brief speaks to children/,
    );
    expect(screen.queryByRole("article", { name: /^Sample script/ })).not.toBeInTheDocument();
  });

  it("explains calmly when no script writer is ready and links to Providers", async () => {
    disableWriters();
    const { user } = await openSaved("/pipelines/space-facts");

    await user.click(previewCard().getByRole("button", WRITE));

    const notice = await previewCard().findByText(/The script writer is not available/);
    expect(notice.closest(".callout")).toHaveClass("callout-info");
    expect(previewCard().getByRole("link", { name: "Open Providers" })).toHaveAttribute(
      "href",
      "/providers",
    );
  });
});
