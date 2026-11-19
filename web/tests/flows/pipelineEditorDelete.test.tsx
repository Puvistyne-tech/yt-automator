import { screen, waitFor } from "@testing-library/react";
import { db } from "@/api/mocks/db";
import {
  cancelDialog,
  confirmDialog,
  findDialog,
  findToast,
  pathOf,
  renderApp,
} from "../helpers/renderApp";

const TITLE = "Delete pipeline?";
const ids = () => db.state.templates.map((t) => t.id);

async function askToDelete(route: string) {
  const app = renderApp(route);
  await app.user.click(await screen.findByRole("button", { name: "Delete" }));
  return { ...app, dialog: await findDialog(TITLE) };
}

describe("Pipeline editor: delete", () => {
  it.each([
    ["without changes", false],
    ["with unsaved changes", true],
  ])("deletes after confirming %s and returns to the list", async (_name, edit) => {
    const app = renderApp("/pipelines/history-five");
    const name = await screen.findByLabelText(/^Name/);
    if (edit) {
      await app.user.type(name, " again");
    }
    await app.user.click(screen.getByRole("button", { name: "Delete" }));

    await confirmDialog(app.user, TITLE, "Delete pipeline");

    await findToast("Deleted “Ancient empires”.");
    await waitFor(() => expect(pathOf(app.router)).toBe("/pipelines"));
    expect(screen.queryByRole("dialog", { name: "Discard unsaved changes?" })).toBeNull();
    expect(ids()).toEqual(["space-facts"]);
  });

  it("keeps the dialog open with the reason when automations still use it", async () => {
    const { user, dialog, router } = await askToDelete("/pipelines/space-facts");

    await user.click(dialog.getByRole("button", { name: "Delete pipeline" }));

    const alert = await dialog.findByRole("alert");
    expect(alert).toHaveTextContent("This pipeline is still in use.");
    expect(alert).toHaveTextContent("template is used by automations: Space facts weekly");
    expect(pathOf(router)).toBe("/pipelines/space-facts");
    expect(ids()).toHaveLength(2);
  });

  it("changes nothing when cancelled", async () => {
    const { user, router } = await askToDelete("/pipelines/history-five");

    await cancelDialog(user, TITLE);

    expect(pathOf(router)).toBe("/pipelines/history-five");
    expect(ids()).toHaveLength(2);
  });

  it("is not offered for a built-in pipeline", async () => {
    renderApp("/pipelines/kids_story");
    expect(await screen.findByRole("button", { name: /Duplicate to customise/ })).toBeVisible();
    expect(screen.queryByRole("button", { name: "Delete" })).not.toBeInTheDocument();
  });
});
