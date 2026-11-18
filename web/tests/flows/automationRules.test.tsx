import { screen, within } from "@testing-library/react";
import { db } from "@/api/mocks/db";
import { findSection, sectionByName, targetRow } from "../helpers/editor";
import { findToast, renderApp } from "../helpers/renderApp";
import { openRun } from "../helpers/runs";
import { failWith } from "../helpers/server";

const stored = (id: string) => db.state.automations.find((a) => a.id === id);

async function openEditor(id: string) {
  const app = renderApp(`/automations/${id}`);
  await findSection("General");
  return app;
}

describe("Automation editor: publishing and schedule rules", () => {
  it("shows a configured automation's rules and a plain summary", async () => {
    await openEditor("auto-shorts");

    const review = sectionByName("Review");
    expect(review.getByRole("switch", { name: "Reject low scores automatically" })).toBeChecked();
    expect(review.getByLabelText(/^Reject below score/)).toHaveValue(60);
    expect(
      review.getByRole("switch", { name: "Publish as soon as a run is approved" }),
    ).toBeChecked();
    expect(
      review.getByText(/^Runs every 6 hours, 08:00 to 20:00 \(Asia\/Kolkata\)/),
    ).toHaveTextContent(/Goes public at 18:00 \(Asia\/Kolkata\)\.$/);
    const schedule = sectionByName("Schedule");
    expect(schedule.getByLabelText(/^From/)).toHaveValue("08:00");
    expect(schedule.getByLabelText(/^At most/)).toHaveValue(2);
    expect(schedule.getByLabelText(/^Retry automatically/)).toHaveValue(2);
    expect(targetRow(1).getByLabelText(/^Go public at/)).toHaveValue("18:00");
  });

  it("saves review, schedule and target rules from the editor", async () => {
    const { user } = await openEditor("auto-bedtime");

    const review = sectionByName("Review");
    await user.click(review.getByRole("switch", { name: "Reject low scores automatically" }));
    await user.click(review.getByRole("switch", { name: "Publish as soon as a run is approved" }));
    const schedule = sectionByName("Schedule");
    await user.click(schedule.getByRole("switch", { name: "Only start during active hours" }));
    await user.click(schedule.getByRole("switch", { name: "Limit runs per day" }));
    await user.click(
      schedule.getByRole("switch", { name: "Skip a start while the last run is unfinished" }),
    );
    const retries = schedule.getByLabelText(/^Retry automatically/);
    await user.clear(retries);
    await user.type(retries, "3");
    await user.selectOptions(targetRow(1).getByLabelText(/^Privacy/), "public");
    await user.selectOptions(targetRow(1).getByLabelText(/^Publish time/), "time");
    expect(targetRow(1).getByText(/^Only public videos are scheduled/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Save changes" }));

    await findToast(/^Saved/);
    expect(stored("auto-bedtime")).toMatchObject({
      review_policy: { reject_below: 50, auto_publish: true },
      schedule: {
        active_from: "08:00",
        active_until: "20:00",
        max_runs_per_day: 2,
        skip_if_unfinished: false,
      },
      retry_policy: { auto_retry_count: 3, retry_delay_minutes: 10 },
    });
    expect(stored("auto-bedtime")?.targets[0]).toMatchObject({
      privacy: "public",
      publish_delay_minutes: 0,
      publish_time_of_day: "18:00",
      publish_timezone: "Asia/Kolkata",
    });
  });

  it("blocks a reject score at or above the auto-approve score", async () => {
    const { user } = await openEditor("auto-shorts");

    const reject = sectionByName("Review").getByLabelText(/^Reject below score/);
    await user.clear(reject);
    await user.type(reject, "95");
    await user.click(screen.getByRole("button", { name: "Save changes" }));

    await findToast("Fix the highlighted fields before saving.");
    expect(
      sectionByName("Review").getByText("Keep this below the auto-approve score (90)."),
    ).toBeInTheDocument();
  });

  it("routes server errors for the new rules to their fields", async () => {
    failWith("put", "/automations/auto-shorts", 400, {
      code: "validation_failed",
      message: "Validation failed",
      fields: {
        "retry_policy.retry_delay_minutes": "Input should be less than or equal to 1440",
        "schedule.active_from": "the schedule never starts inside the active hours",
        "targets.0.publish_time_of_day": "choose a publish delay or a time of day, not both",
      },
    });
    const { user } = await openEditor("auto-shorts");

    await user.type(sectionByName("General").getByLabelText(/^Name/), "!");
    await user.click(screen.getByRole("button", { name: "Save changes" }));

    await findToast("Validation failed");
    const schedule = sectionByName("Schedule");
    expect(schedule.getByText("Input should be less than or equal to 1440")).toBeInTheDocument();
    expect(
      schedule.getByText("the schedule never starts inside the active hours"),
    ).toBeInTheDocument();
    expect(
      targetRow(1).getByText("choose a publish delay or a time of day, not both"),
    ).toBeInTheDocument();
    const nav = screen.getByRole("navigation", { name: "Editor sections" });
    expect(nav).toHaveTextContent("Schedule2");
  });
});

describe("Run detail: automatic actions", () => {
  const actions = () => within(screen.getByRole("list", { name: "Automatic actions" }));

  it("shows an automatic rejection with its reason", async () => {
    await openRun("run-rejected");

    expect(actions().getByText("Rejected automatically")).toBeInTheDocument();
    expect(
      actions().getByText(
        "Rejected automatically: the score 52.5 is below the auto-reject threshold 60",
      ),
    ).toBeInTheDocument();
  });

  it("shows a pending retry and the retries already made", async () => {
    await openRun("run-failed");

    expect(actions().getByText("Retrying automatically")).toBeInTheDocument();
    expect(actions().getByText(/^Attempt 2 of 2 starts at/)).toBeInTheDocument();
    expect(actions().getByText("Retried automatically")).toBeInTheDocument();
  });

  it("shows a skipped scheduled start", async () => {
    await openRun("run-live");

    expect(actions().getByText("Scheduled start skipped")).toBeInTheDocument();
    expect(
      actions().getByText(/^Scheduled start at 2026-01-05 18:00 Asia\/Kolkata skipped/),
    ).toBeInTheDocument();
  });

  it("shows nothing when the rules did nothing", async () => {
    await openRun("run-review");

    expect(screen.queryByRole("list", { name: "Automatic actions" })).not.toBeInTheDocument();
  });
});
