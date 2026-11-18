import { screen, waitFor } from "@testing-library/react";
import { db } from "@/api/mocks/db";
import { findSection, sectionByName, targetRow } from "../helpers/editor";
import { findDialog, findToast, pathOf, renderApp } from "../helpers/renderApp";
import { failWith } from "../helpers/server";

const byName = (name: string) => db.state.automations.find((a) => a.name === name);

async function openNew() {
  const app = renderApp("/automations/new");
  const general = await findSection("General");
  return { ...app, general };
}

describe("Automation editor: create", () => {
  it("creates an automation end to end with languages, targets and a cron schedule", async () => {
    const { user, router, general } = await openNew();

    await user.type(general.getByLabelText(/^Name/), "Morning tales");
    await user.click(sectionByName("Languages").getByRole("checkbox", { name: /^Tamil/ }));
    const targets = sectionByName("Targets");
    await user.click(targets.getByRole("button", { name: "Add target" }));
    await user.click(targets.getByRole("button", { name: "Add target" }));
    await user.selectOptions(targetRow(2).getByLabelText(/^Language/), "ta");
    await user.selectOptions(targetRow(2).getByLabelText(/^Channel/), "chan-ta");
    await user.click(targetRow(2).getByRole("checkbox", { name: /^Short/ }));
    const schedule = sectionByName("Schedule");
    await user.click(schedule.getByRole("radio", { name: /Cron expression/ }));
    const cron = schedule.getByRole("textbox", { name: /^Cron expression/ });
    await user.clear(cron);
    await user.type(cron, "30 7 * * 1-5");
    expect(schedule.getByText("Every weekday at 07:30 (Asia/Kolkata)")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Create automation" }));

    await findToast("Saved “Morning tales”.");
    const saved = byName("Morning tales");
    expect(saved).toMatchObject({
      pipeline_type: "kids_story",
      languages: ["en", "ta"],
      schedule: { kind: "cron", cron: "30 7 * * 1-5", every_hours: null, timezone: "Asia/Kolkata" },
    });
    expect(
      saved?.targets.map((t) => [t.channel_id, t.language, t.variants, t.made_for_kids]),
    ).toEqual([
      ["chan-en", "en", ["episode", "short"], true],
      ["chan-ta", "ta", ["episode"], true],
    ]);
    await waitFor(() => expect(pathOf(router)).toBe(`/automations/${saved?.id}`));
  });

  it("blocks saving and flags each section when the draft is invalid", async () => {
    const { user, general } = await openNew();

    await user.click(sectionByName("Languages").getByRole("checkbox", { name: /^English/ }));
    await user.click(screen.getByRole("button", { name: "Create automation" }));

    await findToast("Fix the highlighted fields before saving.");
    expect(general.getByText("Give the automation a name.")).toBeInTheDocument();
    expect(
      sectionByName("Languages").getByText("Choose at least one language."),
    ).toBeInTheDocument();
    const nav = screen.getByRole("navigation", { name: "Editor sections" });
    expect(nav).toHaveTextContent("General1");
    expect(db.state.automations).toHaveLength(3);
  });

  it("shows server field errors on the matching inputs", async () => {
    failWith("post", "/automations", 400, {
      code: "validation_failed",
      message: "Validation failed",
      fields: { "targets.0.channel_id": "Channel was disconnected." },
    });
    const { user, general } = await openNew();

    await user.type(general.getByLabelText(/^Name/), "Server says no");
    await user.click(sectionByName("Targets").getByRole("button", { name: "Add target" }));
    await user.click(screen.getByRole("button", { name: "Create automation" }));

    await findToast("Validation failed");
    expect(await targetRow(1).findByText("Channel was disconnected.")).toBeInTheDocument();
    expect(targetRow(1).getByLabelText(/^Channel/)).toHaveAttribute("aria-invalid", "true");

    await user.type(general.getByLabelText(/^Name/), "!");
    expect(targetRow(1).queryByText("Channel was disconnected.")).not.toBeInTheDocument();
  });

  it("asks before leaving with unsaved changes", async () => {
    const { user, router, general } = await openNew();

    await user.type(general.getByLabelText(/^Name/), "Draft");
    await user.click(screen.getByRole("link", { name: "Cancel" }));
    const dialog = await findDialog("Discard unsaved changes?");
    await user.click(dialog.getByRole("button", { name: "Keep editing" }));
    expect(pathOf(router)).toBe("/automations/new");

    await user.click(screen.getByRole("link", { name: "Cancel" }));
    await user.click(
      (await findDialog("Discard unsaved changes?")).getByRole("button", {
        name: "Discard changes",
      }),
    );
    await waitFor(() => expect(pathOf(router)).toBe("/automations"));
  });
});

describe("Automation editor: edit", () => {
  it("loads an automation, edits its content settings and schedule, and saves", async () => {
    const { user } = renderApp("/automations/auto-shorts");
    expect(
      await screen.findByRole("heading", { level: 1, name: "Tamil shorts" }),
    ).toBeInTheDocument();
    const content = sectionByName("Content");

    const series = content.getByLabelText(/^Series name/);
    await user.clear(series);
    await user.type(series, "Moonlight tales");
    const hours = sectionByName("Schedule").getByLabelText(/^Every \(hours\)/);
    await user.clear(hours);
    await user.type(hours, "12");
    expect(screen.getByText("Unsaved changes")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Save changes" }));

    await findToast("Saved “Tamil shorts”.");
    const saved = db.state.automations.find((a) => a.id === "auto-shorts");
    expect(saved?.settings.series_name).toBe("Moonlight tales");
    expect(saved?.schedule.every_hours).toBe(12);
    expect(saved?.targets[0]?.id).toBe("target-ta-short");
    expect(screen.getByText("All changes saved")).toBeInTheDocument();
  });

  it("keeps unsaved changes when saving an existing automation fails", async () => {
    failWith("put", "/automations/:id", 500, { message: "Disk full." });
    const { user } = renderApp("/automations/auto-shorts");
    const general = await findSection("General");

    await user.type(general.getByLabelText(/^Name/), " v2");
    await user.click(screen.getByRole("button", { name: "Save changes" }));

    await findToast("Disk full.");
    expect(screen.getByText("Unsaved changes")).toBeInTheDocument();
    expect(byName("Tamil shorts")).toBeDefined();
  });

  it("resets the saved state after each successful save", async () => {
    const { user } = renderApp("/automations/auto-shorts");
    const general = await findSection("General");
    const name = general.getByLabelText(/^Name/);

    await user.type(name, " v2");
    await user.click(screen.getByRole("button", { name: "Save changes" }));
    await findToast("Saved “Tamil shorts v2”.");
    expect(screen.getByText("All changes saved")).toBeInTheDocument();

    await user.type(name, "3");
    expect(screen.getByText("Unsaved changes")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Save changes" }));
    await findToast("Saved “Tamil shorts v23”.");
    expect(screen.getByText("All changes saved")).toBeInTheDocument();
  });

  it("checks the minimum score of the auto-approve review rule", async () => {
    const { user } = renderApp("/automations/auto-shorts");
    const review = await findSection("Review");
    const score = review.getByLabelText(/^Minimum score/);

    await user.clear(score);
    await user.type(score, "101");
    await user.click(screen.getByRole("button", { name: "Save changes" }));

    expect(review.getByText("Use a score between 0 and 100.")).toBeInTheDocument();
  });

  it("flags targets whose language is removed and can remove them", async () => {
    const { user } = renderApp("/automations/auto-bedtime");
    const languages = await findSection("Languages");

    await user.click(languages.getByRole("checkbox", { name: /^Tamil/ }));

    expect(languages.getByRole("status")).toHaveTextContent(
      "1 target still publish in Tamil, which is no longer selected.",
    );
    expect(targetRow(2).getByLabelText(/^Language/)).toHaveDisplayValue("Tamil (not selected)");
    await user.click(languages.getByRole("button", { name: "Remove 1 target" }));
    expect(screen.queryByRole("listitem", { name: "Target 2" })).not.toBeInTheDocument();
  });

  it("locks made for kids on kids pipelines", async () => {
    renderApp("/automations/auto-bedtime");
    await findSection("Targets");

    expect(targetRow(1).getByRole("switch", { name: /Made for kids/ })).toBeDisabled();
  });
});
