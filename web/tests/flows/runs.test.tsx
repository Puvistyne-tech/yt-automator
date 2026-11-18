import { screen, waitFor, within } from "@testing-library/react";
import { db } from "@/api/mocks/db";
import { findDialog, findToast, pathOf, renderApp } from "../helpers/renderApp";

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
  });

  it("approves a run, then publishes it and lists the uploads", async () => {
    const { user } = await openRun("run-review");

    await user.type(screen.getByLabelText("Review notes"), "Looks great");
    await user.click(screen.getByRole("button", { name: "Approve" }));
    await findToast("Run approved. You can publish it now.");
    expect(run("run-review")?.review).toMatchObject({ decision: "approved", notes: "Looks great" });

    await user.click(await screen.findByRole("button", { name: "Publish" }));
    await user.click(
      (await findDialog("Publish this run?")).getByRole("button", { name: "Publish now" }),
    );

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
    await user.click(
      (await findDialog("Delete this run?")).getByRole("button", { name: "Delete run" }),
    );

    await findToast("Run deleted.");
    expect(run("run-published")).toBeUndefined();
    await waitFor(() => expect(pathOf(router)).toBe("/runs"));
  });

  it("shows an error state for an unknown run", async () => {
    renderApp("/runs/nope");

    expect(await screen.findByText("Run was not found.")).toBeInTheDocument();
  });
});
