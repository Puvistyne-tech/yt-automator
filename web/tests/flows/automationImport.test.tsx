import { screen, type within } from "@testing-library/react";
import { exportDocument } from "@/api/mocks/automationImport";
import { db } from "@/api/mocks/db";
import type { AutomationDocument } from "@/api/types";
import { exportFile } from "../helpers/downloads";
import { cancelDialog, findDialog, findRow, findToast, renderApp } from "../helpers/renderApp";

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

  it("refuses unknown keys like the backend", async () => {
    const document = bedtimeDocument();
    const [first, ...rest] = document.automation.targets;
    const { dialog } = await openImport({
      ...document,
      extra: true,
      automation: { ...document.automation, targets: [{ ...first, id: "t-1" }, ...rest] },
    });

    const problems = await dialog.findByText("This file cannot be imported as it is:");
    expect(problems.parentElement).toHaveTextContent("Extra: Extra inputs are not permitted");
    expect(problems.parentElement).toHaveTextContent(
      "Targets › 1 › id: Extra inputs are not permitted",
    );
    expect(importButton(dialog)).toBeDisabled();
  });

  it("creates nothing when cancelled", async () => {
    const before = db.state.automations.length;
    const { user } = await openImport(bedtimeDocument());

    await cancelDialog(user, "Import automation");

    expect(screen.queryByRole("dialog", { name: "Import automation" })).toBeNull();
    expect(db.state.automations).toHaveLength(before);
  });
});
