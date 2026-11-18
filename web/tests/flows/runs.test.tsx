import { screen, waitFor, within } from "@testing-library/react";
import { db } from "@/api/mocks/db";
import {
  cancelDialog,
  confirmDialog,
  findDialog,
  findToast,
  pathOf,
  renderApp,
} from "../helpers/renderApp";
import { failWith } from "../helpers/server";

const run = (id: string) => db.state.runs.find((r) => r.id === id);

async function openRun(id: string) {
  const app = renderApp(`/runs/${id}`);
  await screen.findByRole("heading", { level: 1 });
  return app;
}

describe("Runs list", () => {
  it("lists runs and filters by status and automation through the url", async () => {
    const { user, router } = renderApp("/runs");
    const table = await screen.findByRole("table", { name: "Runs" });
    expect(within(table).getAllByRole("row")).toHaveLength(6);
    expect(within(table).getAllByRole("link", { name: "Tamil shorts" })).toHaveLength(2);

    await user.selectOptions(screen.getByLabelText("Status"), "failed");
    await waitFor(() =>
      expect(within(screen.getByRole("table", { name: "Runs" })).getAllByRole("row")).toHaveLength(
        2,
      ),
    );
    expect(router.state.location.search).toBe("?status=failed");

    await user.selectOptions(screen.getByLabelText("Automation"), "auto-bedtime");
    expect(await screen.findByText("No runs match these filters")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Clear filters" }));
    await waitFor(() => expect(router.state.location.search).toBe(""));
  });

  it("shows an empty state without runs", async () => {
    db.state.runs = [];
    renderApp("/runs");

    expect(await screen.findByText("No runs yet")).toBeInTheDocument();
  });
});

describe("Run detail", () => {
  it("shows stages, artifacts grouped by language and output, and the score", async () => {
    const { user } = await openRun("run-review");

    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Bedtime stories");
    expect(await screen.findByText("English — Episode · 16:9")).toBeInTheDocument();
    expect(screen.getByText("Tamil — Episode · 16:9")).toBeInTheDocument();
    await user.click(screen.getByRole("tab", { name: "Score" }));
    expect(screen.getByRole("tabpanel")).toHaveTextContent("91.4");
    expect(screen.getByRole("tabpanel")).toHaveTextContent("Review rule: always");
  });

  it("shows the auto-approve review rule next to the score", async () => {
    await openRun("run-failed");

    expect(screen.getByText("auto-approve at 90+")).toBeInTheDocument();
  });

  it("shows why an upload was skipped", async () => {
    await openRun("run-published");

    const uploads = await screen.findByRole("table", { name: "Uploads" });
    expect(within(uploads).getByText("Skipped")).toBeInTheDocument();
    expect(within(uploads).getByText("Language ta is not in this run.")).toBeInTheDocument();
    expect(screen.getByText("1 uploaded · 1 failed · 0 pending · 1 skipped")).toBeInTheDocument();
  });

  it("approves a run, then publishes it and lists the uploads", async () => {
    const { user } = await openRun("run-review");

    await user.type(screen.getByLabelText("Review notes"), "Looks great");
    await user.click(screen.getByRole("button", { name: "Approve" }));
    await findToast("Run approved. You can publish it now.");
    expect(run("run-review")?.review).toMatchObject({ decision: "approved", notes: "Looks great" });

    await user.click(await screen.findByRole("button", { name: "Publish" }));
    await confirmDialog(user, "Publish this run?", "Publish now");

    await findToast("Publishing started.");
    const uploads = await screen.findByRole("table", { name: "Uploads" });
    expect(within(uploads).getAllByRole("row")).toHaveLength(4);
    expect(screen.getByText("3 uploaded · 0 failed · 0 pending")).toBeInTheDocument();
    expect(run("run-review")?.status).toBe("published");
  });

  it("rejects a run", async () => {
    const { user } = await openRun("run-review");

    await user.click(screen.getByRole("button", { name: "Reject" }));

    await findToast("Run rejected.");
    expect(run("run-review")?.status).toBe("rejected");
    await waitFor(() =>
      expect(screen.queryByRole("button", { name: "Approve" })).not.toBeInTheDocument(),
    );
  });

  it("retries a failed run from the failed stage", async () => {
    const { user } = await openRun("run-failed");
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Narrate: the Tamil voice model is not installed.",
    );

    await user.click(screen.getByRole("button", { name: "Retry…" }));
    const dialog = await findDialog("Retry run");
    const failedStage = run("run-failed")?.stages[3]?.stage_id;
    expect(dialog.getByLabelText("Start from stage")).toHaveValue(failedStage);
    await user.click(dialog.getByRole("button", { name: "Retry from stage" }));

    await findToast("Retry queued.");
    expect(run("run-failed")).toMatchObject({ status: "queued", error: null });
    expect(run("run-failed")?.stages[2]?.status).toBe("done");
    expect(run("run-failed")?.stages[3]?.status).toBe("pending");
  });

  it("cancels a running run after confirmation", async () => {
    const { user } = await openRun("run-live");

    await user.click(screen.getByRole("button", { name: "Cancel run" }));
    const dialog = await findDialog("Cancel this run?");
    await user.click(dialog.getByRole("button", { name: "Cancel run" }));

    await findToast("Run cancelled.");
    expect(run("run-live")?.status).toBe("cancelled");
  });

  it("deletes a run after confirmation and returns to the list", async () => {
    const { user, router } = await openRun("run-published");

    await user.click(screen.getByRole("button", { name: "Delete" }));
    await confirmDialog(user, "Delete this run?", "Delete run");

    await findToast("Run deleted.");
    expect(run("run-published")).toBeUndefined();
    await waitFor(() => expect(pathOf(router)).toBe("/runs"));
  });

  it.each([
    ["Approve", "/runs/:id/review"],
    ["Reject", "/runs/:id/review"],
  ])("reports a failed %s and keeps the run awaiting review", async (button, path) => {
    failWith("post", path, 409, { message: "The run changed meanwhile." });
    const { user } = await openRun("run-review");

    await user.click(screen.getByRole("button", { name: button }));

    await findToast("The run changed meanwhile.");
    expect(run("run-review")?.status).toBe("awaiting_review");
    expect(screen.getByRole("button", { name: "Approve" })).toBeEnabled();
  });

  it("reports a failed publish and closes the dialog", async () => {
    failWith("post", "/runs/:id/publish", 409, { message: "Not enough quota left today." });
    db.state.runs = db.state.runs.map((r) =>
      r.id === "run-review" ? { ...r, status: "approved" } : r,
    );
    const { user } = await openRun("run-review");

    await user.click(screen.getByRole("button", { name: "Publish" }));
    await confirmDialog(user, "Publish this run?", "Publish now");

    await findToast("Not enough quota left today.");
    await waitFor(() =>
      expect(screen.queryByRole("dialog", { name: "Publish this run?" })).not.toBeInTheDocument(),
    );
    expect(run("run-review")?.status).toBe("approved");
  });

  it.each([
    ["run-failed", "Retry…", "Retry run", "Retry from stage", "post", "/runs/:id/retry", "failed"],
    [
      "run-live",
      "Cancel run",
      "Cancel this run?",
      "Cancel run",
      "post",
      "/runs/:id/cancel",
      "running",
    ],
    [
      "run-published",
      "Delete",
      "Delete this run?",
      "Delete run",
      "delete",
      "/runs/:id",
      "published",
    ],
  ] as const)(
    "reports a failed action on %s and leaves it unchanged",
    async (id, trigger, title, confirm, method, path, status) => {
      failWith(method, path, 500, { message: "The worker is busy." });
      const { user } = await openRun(id);

      await user.click(screen.getByRole("button", { name: trigger }));
      await confirmDialog(user, title, confirm);

      await findToast("The worker is busy.");
      expect(run(id)?.status).toBe(status);
      await waitFor(() =>
        expect(screen.queryByRole("dialog", { name: title })).not.toBeInTheDocument(),
      );
    },
  );

  it.each([
    ["run-failed", "Retry…", "Retry run", "Cancel", "failed"],
    ["run-live", "Cancel run", "Cancel this run?", "Keep running", "running"],
    ["run-published", "Delete", "Delete this run?", "Cancel", "published"],
  ] as const)(
    "dismisses the %s dialog without changing the run",
    async (id, trigger, title, dismiss, status) => {
      const { user } = await openRun(id);

      await user.click(screen.getByRole("button", { name: trigger }));
      await cancelDialog(user, title, dismiss);

      expect(run(id)?.status).toBe(status);
    },
  );

  it("dismisses the publish dialog without publishing", async () => {
    db.state.runs = db.state.runs.map((r) =>
      r.id === "run-review" ? { ...r, status: "approved" } : r,
    );
    const { user } = await openRun("run-review");

    await user.click(screen.getByRole("button", { name: "Publish" }));
    await cancelDialog(user, "Publish this run?");

    expect(run("run-review")).toMatchObject({ status: "approved", uploads: [] });
  });

  it("shows an error state for an unknown run", async () => {
    renderApp("/runs/nope");

    expect(await screen.findByText("Run was not found.")).toBeInTheDocument();
  });
});
