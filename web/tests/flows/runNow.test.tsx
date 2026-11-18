import { act, screen, waitFor } from "@testing-library/react";
import { db } from "@/api/mocks/db";
import { findRow, findToast, pathOf, renderApp } from "../helpers/renderApp";
import { failWith } from "../helpers/server";

const LIST = {
  name: "the automations list",
  route: "/automations",
  find: async () =>
    (await findRow("Automations", "Tamil shorts")).getByRole("button", {
      name: "Run Tamil shorts now",
    }),
};

const EDITOR = {
  name: "the automation editor",
  route: "/automations/auto-shorts",
  find: () => screen.findByRole("button", { name: "Run now" }),
};

const ENTRY_POINTS = [LIST, EDITOR];

async function startRun(route: string, find: () => Promise<HTMLElement>) {
  const app = renderApp(route);
  const known = db.state.runs.map((r) => r.id);
  await app.user.click(await find());
  return { ...app, known };
}

const queuedRun = (known: string[]) => db.state.runs.find((r) => !known.includes(r.id));

describe.each(ENTRY_POINTS)("Run now from $name", ({ route, find }) => {
  it("queues a run and links the toast to it", async () => {
    const { user, router, known } = await startRun(route, find);

    await findToast("Run queued for Tamil shorts.");
    const queued = queuedRun(known);
    expect(queued?.automation_id).toBe("auto-shorts");
    await user.click(screen.getByRole("button", { name: "View run" }));
    await waitFor(() => expect(pathOf(router)).toBe(`/runs/${queued?.id}`));
    expect(screen.queryByRole("button", { name: "View run" })).not.toBeInTheDocument();
  });

  it("reports a failure without queuing a run", async () => {
    failWith("post", "/automations/:id/runs", 409, { message: "Pipeline is not installed." });
    const { known } = await startRun(route, find);

    await findToast("Pipeline is not installed.");
    expect(db.state.runs).toHaveLength(known.length);
    expect(screen.queryByRole("button", { name: "View run" })).not.toBeInTheDocument();
  });
});

describe("Run queued toast", () => {
  it("still opens the run after the user moved to another page", async () => {
    const { user, router, known } = await startRun(LIST.route, LIST.find);
    await findToast("Run queued for Tamil shorts.");

    await act(() => router.navigate("/channels"));
    await user.click(screen.getByRole("button", { name: "View run" }));

    await waitFor(() => expect(pathOf(router)).toBe(`/runs/${queuedRun(known)?.id}`));
  });

  it("closes on Dismiss without opening the run", async () => {
    const { user, router } = await startRun(LIST.route, LIST.find);
    await findToast("Run queued for Tamil shorts.");

    await user.click(screen.getByRole("button", { name: "Dismiss notification" }));

    expect(screen.queryByRole("button", { name: "View run" })).not.toBeInTheDocument();
    expect(pathOf(router)).toBe("/automations");
  });
});
