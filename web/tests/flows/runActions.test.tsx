import { screen, waitFor } from "@testing-library/react";
import { cancelDialog, confirmDialog, findDialog, findToast, pathOf } from "../helpers/renderApp";
import { openRun, setRunStatus, storedRun } from "../helpers/runs";
import { failWith } from "../helpers/server";

describe("Run actions", () => {
  it("retries a failed run from the failed stage", async () => {
    const { user } = await openRun("run-failed");
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Narrate: the Tamil voice model is not installed.",
    );

    await user.click(screen.getByRole("button", { name: "Retry…" }));
    const dialog = await findDialog("Retry run");
    const failedStage = storedRun("run-failed")?.stages[3]?.stage_id;
    expect(dialog.getByLabelText("Start from stage")).toHaveValue(failedStage);
    await user.click(dialog.getByRole("button", { name: "Retry from stage" }));

    await findToast("Retry queued.");
    expect(storedRun("run-failed")).toMatchObject({ status: "queued", error: null });
    expect(storedRun("run-failed")?.stages[2]?.status).toBe("done");
    expect(storedRun("run-failed")?.stages[3]?.status).toBe("pending");
  });

  it("cancels a running run after confirmation", async () => {
    const { user } = await openRun("run-live");

    await user.click(screen.getByRole("button", { name: "Cancel run" }));
    await confirmDialog(user, "Cancel this run?", "Cancel run");

    await findToast("Run cancelled.");
    expect(storedRun("run-live")?.status).toBe("cancelled");
  });

  it("deletes a run after confirmation and returns to the list", async () => {
    const { user, router } = await openRun("run-published");

    await user.click(screen.getByRole("button", { name: "Delete" }));
    await confirmDialog(user, "Delete this run?", "Delete run");

    await findToast("Run deleted.");
    expect(storedRun("run-published")).toBeUndefined();
    await waitFor(() => expect(pathOf(router)).toBe("/runs"));
  });

  it("reports the conflict when the run changed status meanwhile", async () => {
    const { user } = await openRun("run-live");
    setRunStatus("run-live", "published");

    await user.click(screen.getByRole("button", { name: "Cancel run" }));
    await confirmDialog(user, "Cancel this run?", "Cancel run");

    await findToast("run run-live cannot move from published to cancelled");
    expect(storedRun("run-live")?.status).toBe("published");
  });

  it.each([
    ["run-failed", "failed", "Retry…", "Retry run", "Retry from stage", "post", "/runs/:id/retry"],
    [
      "run-live",
      "running",
      "Cancel run",
      "Cancel this run?",
      "Cancel run",
      "post",
      "/runs/:id/cancel",
    ],
    [
      "run-published",
      "published",
      "Delete",
      "Delete this run?",
      "Delete run",
      "delete",
      "/runs/:id",
    ],
    [
      "run-review",
      "approved",
      "Publish",
      "Publish this run?",
      "Publish now",
      "post",
      "/runs/:id/publish",
    ],
  ] as const)(
    "reports a failed action on %s and leaves it %s",
    async (id, status, trigger, title, confirm, method, path) => {
      failWith(method, path, 500, { message: "The worker is busy." });
      setRunStatus(id, status);
      const { user } = await openRun(id);

      await user.click(screen.getByRole("button", { name: trigger }));
      await confirmDialog(user, title, confirm);

      await findToast("The worker is busy.");
      expect(storedRun(id)?.status).toBe(status);
      await waitFor(() =>
        expect(screen.queryByRole("dialog", { name: title })).not.toBeInTheDocument(),
      );
    },
  );

  it.each([
    ["run-failed", "failed", "Retry…", "Retry run", "Cancel"],
    ["run-live", "running", "Cancel run", "Cancel this run?", "Keep running"],
    ["run-published", "published", "Delete", "Delete this run?", "Cancel"],
    ["run-review", "approved", "Publish", "Publish this run?", "Cancel"],
  ] as const)(
    "dismisses the %s dialog and leaves it %s",
    async (id, status, trigger, title, dismiss) => {
      setRunStatus(id, status);
      const { user } = await openRun(id);

      await user.click(screen.getByRole("button", { name: trigger }));
      await cancelDialog(user, title, dismiss);

      expect(storedRun(id)?.status).toBe(status);
    },
  );
});
