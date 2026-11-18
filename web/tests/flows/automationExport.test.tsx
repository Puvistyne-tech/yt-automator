import { screen, waitFor, within } from "@testing-library/react";
import { captureDownloads } from "../helpers/downloads";
import { findSection } from "../helpers/editor";
import { findRow, findToast, renderApp } from "../helpers/renderApp";

afterEach(() => vi.restoreAllMocks());

describe("Automation export", () => {
  it("downloads one automation from the list as a portable JSON file", async () => {
    const downloads = captureDownloads();
    const { user } = renderApp("/automations");
    const row = await findRow("Automations", "Bedtime stories");

    await user.click(row.getByRole("button", { name: "Export Bedtime stories" }));

    await findToast("Exported “Bedtime stories” to bedtime-stories.autotube.json.");
    expect(downloads.map((download) => download.filename)).toEqual([
      "bedtime-stories.autotube.json",
    ]);
    const document = await downloads[0]?.json();
    expect(document).toMatchObject({ app: "AutoTube", format_version: 1 });
    expect(Object.keys(document?.automation as object).sort()).toEqual(
      [
        "description",
        "languages",
        "name",
        "pipeline_type",
        "retry_policy",
        "review_policy",
        "schedule",
        "settings",
        "targets",
      ].sort(),
    );
    const text = JSON.stringify(document);
    expect(text).not.toMatch(/secret|token|cred-main|target-en/);
  });

  it("exports the saved automation from the editor", async () => {
    const downloads = captureDownloads();
    const { user } = renderApp("/automations/auto-shorts");
    await findSection("General");

    await user.click(screen.getByRole("button", { name: "Export" }));

    await findToast("Exported “Tamil shorts” to tamil-shorts.autotube.json.");
    expect((await downloads[0]?.json())?.automation).toMatchObject({ name: "Tamil shorts" });
  });

  it("offers no export before an automation is saved", async () => {
    renderApp("/automations/new");
    await findSection("General");

    expect(screen.queryByRole("button", { name: "Export" })).not.toBeInTheDocument();
  });
});

describe("Content settings defaults", () => {
  it("marks changed settings in the editor and resets a section", async () => {
    const { user } = renderApp("/automations/auto-bedtime");
    const content = await findSection("Content");
    const name = content.getByLabelText(/^Series name/);

    await user.type(name, " Plus");
    const story = within(content.getByRole("region", { name: "Story" }));
    expect(story.getByRole("button", { name: "Reset Series name to default" })).toBeVisible();
    expect(story.getByText("1 changed")).toBeInTheDocument();
    await user.click(story.getByRole("button", { name: "Reset Story section to defaults" }));

    expect(name).toHaveValue("Story Time");
    await waitFor(() => expect(story.queryByText("1 changed")).not.toBeInTheDocument());
  });
});
