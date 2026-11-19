import { screen } from "@testing-library/react";
import { db } from "@/api/mocks/db";
import { makeTarget } from "@/api/mocks/fixtures/factories";
import {
  ADVANCED_PLATFORM_FIELDS,
  type AdvancedField,
} from "@/features/automation-editor/model/settingsView";
import { findSection, sectionByName, startInAllSettings, targetRow } from "../helpers/editor";
import { findToast, renderApp } from "../helpers/renderApp";

const stored = () => db.state.automations.find((a) => a.id === "auto-shorts");

const CONTROLS: Record<AdvancedField, () => HTMLElement | null> = {
  description: () => sectionByName("General").queryByLabelText(/^Description/),
  timezone: () => sectionByName("Schedule").queryByLabelText(/^Timezone/),
  schedule_limits: () =>
    sectionByName("Schedule").queryByRole("switch", { name: "Limit runs per day" }),
  retry_policy: () => sectionByName("Schedule").queryByLabelText(/^Retry automatically/),
  playlist: () => targetRow(1).queryByLabelText(/^Playlist/),
  publish_timing: () => targetRow(1).queryByLabelText(/^Go public at/),
  reject_below: () =>
    sectionByName("Review").queryByRole("switch", { name: "Reject low scores automatically" }),
};

async function openShorts() {
  const app = renderApp("/automations/auto-shorts");
  await findSection("Content");
  return app;
}

function withFinerRules() {
  const automation = stored();
  if (automation === undefined) {
    return;
  }
  const [first] = automation.targets;
  automation.targets = [
    { ...makeTarget(first), playlist_id: "pl-ta-shorts", publish_timezone: "Asia/Tokyo" },
    makeTarget({ id: "t-delay", channel_id: "chan-ta", language: "ta", publish_delay_minutes: 30 }),
  ];
  automation.schedule = {
    ...automation.schedule,
    timezone: "Europe/Berlin",
    skip_if_unfinished: false,
    max_runs_per_day: 3,
    active_from: "07:00",
    active_until: "21:30",
  };
  automation.review_policy = { ...automation.review_policy, reject_below: 40 };
}

describe("Automation editor: finer rules in Simple", () => {
  it.each(ADVANCED_PLATFORM_FIELDS.map((field) => field.id))(
    "hides %s in Simple and shows it in All settings",
    async (id) => {
      const { user } = await openShorts();
      expect(CONTROLS[id]()).toBeNull();

      await user.click(screen.getByRole("button", { name: /^All settings$/ }));
      expect(CONTROLS[id]()).toBeInTheDocument();
    },
  );

  it("keeps channel, privacy and the minimum score in Simple", async () => {
    await openShorts();

    expect(targetRow(1).getByLabelText(/^Channel/)).toBeInTheDocument();
    expect(targetRow(1).getByLabelText(/^Privacy/)).toBeInTheDocument();
    expect(sectionByName("Review").getByLabelText(/^Minimum score/)).toBeInTheDocument();
  });

  it("keeps hidden schedule, target and review rules when saving from Simple", async () => {
    withFinerRules();
    const before = structuredClone(stored());
    const { user } = await openShorts();

    await user.type(sectionByName("General").getByLabelText(/^Name/), " Plus");
    await user.click(screen.getByRole("button", { name: "Save changes" }));

    await findToast(/^Saved/);
    expect(stored()?.schedule).toEqual(before?.schedule);
    expect(stored()?.targets).toEqual(before?.targets);
    expect(stored()?.review_policy).toEqual(before?.review_policy);
  });

  it("shows every finer rule once All settings is chosen", async () => {
    startInAllSettings();
    await openShorts();

    expect(screen.queryByText(/more options in All settings/)).not.toBeInTheDocument();
  });
});
