import { screen, waitFor } from "@testing-library/react";
import { findToast, pathOf, renderApp, type User } from "../helpers/renderApp";
import { startNewPipeline } from "../helpers/templates";

async function leaveForList(user: User, router: Parameters<typeof pathOf>[0]) {
  await user.click(screen.getByRole("link", { name: "Pipelines", current: false }));
  await waitFor(() => expect(pathOf(router)).toBe("/pipelines"));
  expect(screen.queryByRole("dialog", { name: /Discard unsaved changes/ })).not.toBeInTheDocument();
}

describe("Pipeline editor: unsaved changes", () => {
  it.each(["/pipelines/space-facts", "/pipelines/history-five", "/pipelines/kids_story"])(
    "opens %s with nothing unsaved and leaves without asking",
    async (route) => {
      const { user, router } = renderApp(route);
      await screen.findByLabelText(/^Name/);

      expect(screen.queryByText("Unsaved changes")).not.toBeInTheDocument();
      await leaveForList(user, router);
    },
  );

  it("leaves an untouched new pipeline without asking", async () => {
    const { user, router } = await startNewPipeline("General audience");

    expect(screen.getByText("All changes saved")).toBeInTheDocument();
    await leaveForList(user, router);
  });

  it("counts a real edit as unsaved and is clean again after saving", async () => {
    const { user } = renderApp("/pipelines/space-facts");
    await user.type(await screen.findByLabelText(/^Tone/), " and calm");
    expect(screen.getByText("Unsaved changes")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Save changes" }));

    await findToast("Saved “Space facts”.");
    expect(await screen.findByText("All changes saved")).toBeInTheDocument();
  });
});
