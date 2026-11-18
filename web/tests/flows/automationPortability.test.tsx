import { screen, waitFor, within } from "@testing-library/react";
import { exportDocument } from "@/api/mocks/automationImport";
import { db } from "@/api/mocks/db";
import type { AutomationDocument } from "@/api/types";
import { captureDownloads, exportFile } from "../helpers/downloads";
import { findSection } from "../helpers/editor";
import { cancelDialog, findDialog, findRow, findToast, renderApp } from "../helpers/renderApp";

afterEach(() => vi.restoreAllMocks());

const imported = () => db.state.automations.find((a) => a.name === "Bedtime stories (imported)");

function bedtimeDocument(): AutomationDocument {
  const bedtime = db.state.automations.find((a) => a.id === "auto-bedtime");
  if (bedtime === undefined) {
    throw new Error("seed changed");
  }
  return exportDocument(bedtime, db.state.channels);
}

function withGoneChannel(document: AutomationDocument): AutomationDocument {
  const [first, ...rest] = document.automation.targets;
  if (first === undefined) {
    throw new Error("seed changed");
  }
  return {
    ...document,
    automation: {
      ...document.automation,
      targets: [{ ...first, channel_id: "chan-gone" }, ...rest],
    },
    channels: [{ id: "chan-gone", youtube_channel_id: "UC_gone", title: "Gone channel" }],
  };
}

async function openImport(document: unknown) {
  const app = renderApp("/automations");
  await findRow("Automations", "Bedtime stories");
  await app.user.click(screen.getByRole("button", { name: "Import" }));
  const dialog = await findDialog("Import automation");
  await app.user.upload(dialog.getByLabelText("Export file"), exportFile(document));
  return { ...app, dialog };
}

const importButton = (dialog: ReturnType<typeof within>) =>
  dialog.getByRole("button", { name: "Import automation" });

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

describe("Automation import", () => {
  it("imports an export as a switched-off copy", async () => {
    const { user, dialog } = await openImport(bedtimeDocument());

    expect(await dialog.findByText("“Bedtime stories (imported)”")).toBeInTheDocument();
    await user.click(importButton(dialog));

    await findToast("Imported “Bedtime stories (imported)”. It stays off until you enable it.");
    expect(imported()).toMatchObject({ enabled: false, languages: ["en", "ta"] });
    expect(screen.queryByRole("dialog", { name: "Import automation" })).not.toBeInTheDocument();
  });

  it("asks for a channel that is not connected and maps its targets", async () => {
    const { user, dialog } = await openImport(withGoneChannel(bedtimeDocument()));
    const select = await dialog.findByLabelText("Channel for “Gone channel”");

    await user.click(importButton(dialog));
    expect(await dialog.findByText(/is not connected here: choose a channel/)).toBeInTheDocument();
    await user.selectOptions(select, "chan-ta");
    expect(dialog.queryByText(/is not connected here: choose a channel/)).not.toBeInTheDocument();
    await user.click(importButton(dialog));

    await findToast(/Imported “Bedtime stories \(imported\)”/);
    expect(imported()?.targets.map((target) => target.channel_id)).toEqual(["chan-ta", "chan-ta"]);
  });

  it("leaves out the targets of a channel when asked", async () => {
    const { user, dialog } = await openImport(withGoneChannel(bedtimeDocument()));

    await user.selectOptions(
      await dialog.findByLabelText("Channel for “Gone channel”"),
      "Leave its targets out",
    );
    await user.click(importButton(dialog));

    await findToast(/Imported/);
    expect(imported()?.targets.map((target) => target.channel_id)).toEqual(["chan-ta"]);
  });

  it("refuses a file from a newer AutoTube with the reason", async () => {
    const { dialog } = await openImport({ ...bedtimeDocument(), format_version: 7 });

    expect(await dialog.findByRole("alert")).toHaveTextContent(
      "This file cannot be imported: this file was exported by a newer AutoTube (format 7)",
    );
    expect(importButton(dialog)).toBeDisabled();
  });

  it("refuses a file that is not an export", async () => {
    const { dialog } = await openImport("just text");

    expect(await dialog.findByRole("alert")).toHaveTextContent("does not hold a JSON object");
    expect(importButton(dialog)).toBeDisabled();
  });

  it("lists field errors such as an unknown pipeline", async () => {
    const document = bedtimeDocument();
    const { dialog } = await openImport({
      ...document,
      automation: { ...document.automation, pipeline_type: "comics" },
    });

    const problems = await dialog.findByText("This file cannot be imported as it is:");
    expect(problems.parentElement).toHaveTextContent(
      "Pipeline type: unknown pipeline type 'comics'",
    );
    expect(importButton(dialog)).toBeDisabled();
  });

  it("creates nothing when cancelled", async () => {
    const before = db.state.automations.length;
    const { user } = await openImport(bedtimeDocument());

    await cancelDialog(user, "Import automation");

    expect(db.state.automations).toHaveLength(before);
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
