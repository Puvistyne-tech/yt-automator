import { screen, waitFor, within } from "@testing-library/react";
import { db } from "@/api/mocks/db";
import { STORY_ARTIFACT } from "@/api/mocks/fixtures/artifacts";
import { confirmDialog, findToast } from "../helpers/renderApp";
import { openRun, setRunStatus, storedRun } from "../helpers/runs";
import { failWith } from "../helpers/server";

describe("Run review and publish", () => {
  it("approves a run, then publishes it and lists the uploads", async () => {
    const { user } = await openRun("run-review");

    await user.type(screen.getByLabelText("Review notes"), "Looks great");
    await user.click(screen.getByRole("button", { name: "Approve" }));
    await findToast("Run approved. You can publish it now.");
    expect(storedRun("run-review")?.review).toMatchObject({
      decision: "approved",
      notes: "Looks great",
    });

    await user.click(await screen.findByRole("button", { name: "Publish" }));
    await confirmDialog(user, "Publish this run?", "Publish now");

    await findToast("Publishing started.");
    const uploads = await screen.findByRole("table", { name: "Uploads" });
    expect(within(uploads).getAllByRole("row")).toHaveLength(4);
    expect(screen.getByText("3 uploaded · 0 failed · 0 pending")).toBeInTheDocument();
    expect(storedRun("run-review")?.status).toBe("published");
  });

  it("keeps the run approved with an error when no upload succeeded", async () => {
    db.state.runs = db.state.runs.map((r) =>
      r.id === "run-review" ? { ...r, status: "approved", artifacts: [STORY_ARTIFACT] } : r,
    );
    const { user } = await openRun("run-review");

    await user.click(screen.getByRole("button", { name: "Publish" }));
    await confirmDialog(user, "Publish this run?", "Publish now");

    expect(await screen.findByText("no upload succeeded")).toBeInTheDocument();
    expect(storedRun("run-review")?.status).toBe("approved");
    expect(screen.getByText("No short video for en in this run.")).toBeInTheDocument();
  });

  it("rejects a run", async () => {
    const { user } = await openRun("run-review");

    await user.click(screen.getByRole("button", { name: "Reject" }));

    await findToast("Run rejected.");
    expect(storedRun("run-review")?.status).toBe("rejected");
    await waitFor(() =>
      expect(screen.queryByRole("button", { name: "Approve" })).not.toBeInTheDocument(),
    );
  });

  it.each([
    ["Approve", "/runs/:id/review"],
    ["Reject", "/runs/:id/review"],
  ])("reports a failed %s and keeps the run awaiting review", async (button, path) => {
    failWith("post", path, 409, { message: "The run changed meanwhile." });
    const { user } = await openRun("run-review");

    await user.click(screen.getByRole("button", { name: button }));

    await findToast("The run changed meanwhile.");
    expect(storedRun("run-review")?.status).toBe("awaiting_review");
    expect(screen.getByRole("button", { name: "Approve" })).toBeEnabled();
  });

  it("offers publishing only once approved", async () => {
    setRunStatus("run-review", "approved");
    await openRun("run-review");

    expect(screen.getByRole("button", { name: "Publish" })).toBeEnabled();
    expect(screen.queryByRole("button", { name: "Approve" })).not.toBeInTheDocument();
  });
});
