import { screen } from "@testing-library/react";
import { db } from "@/api/mocks/db";
import {
  cancelDialog,
  confirmDialog,
  findDialog,
  findToast,
  findWithin,
  renderApp,
} from "../helpers/renderApp";
import { captureBody, failWith } from "../helpers/server";

const findCredential = (name: string) => findWithin(name, "li", { selector: ".cell-title" });

describe("Credentials", () => {
  async function openAddDialog() {
    const app = renderApp("/channels");
    await findCredential("Main Google project");
    await app.user.click(
      screen.getAllByRole("button", { name: "Add credential" })[0] as HTMLElement,
    );
    return { ...app, dialog: await findDialog("Add Google API credential") };
  }

  it("adds a credential after validating the secret", async () => {
    const { user, dialog } = await openAddDialog();

    await user.type(dialog.getByLabelText(/^Name/), "Third project");
    await user.type(dialog.getByLabelText(/^Client id/), "9999.apps.googleusercontent.com");
    await user.click(dialog.getByRole("button", { name: "Add credential" }));
    expect(dialog.getByText("Paste the OAuth client secret.")).toBeInTheDocument();

    await user.type(dialog.getByLabelText(/^Client secret/), "shh");
    await user.click(dialog.getByRole("button", { name: "Add credential" }));

    await findToast("Added Third project.");
    expect((await findCredential("Third project")).getByText("Secret stored")).toBeInTheDocument();
    expect(JSON.stringify(db.state.credentials)).not.toContain("shh");
  });

  it("shows server field errors when adding a credential fails", async () => {
    failWith("post", "/credentials", 400, {
      message: "The credential is not valid.",
      fields: { "body.client_id": "This client id is already registered." },
    });
    const { user, dialog } = await openAddDialog();

    await user.type(dialog.getByLabelText(/^Name/), "Again");
    await user.type(dialog.getByLabelText(/^Client id/), "1234-main.apps.googleusercontent.com");
    await user.type(dialog.getByLabelText(/^Client secret/), "shh");
    await user.click(dialog.getByRole("button", { name: "Add credential" }));

    await findToast("The credential is not valid.");
    expect(dialog.getByText("This client id is already registered.")).toBeInTheDocument();
    expect(db.state.credentials).toHaveLength(2);
  });

  it("edits a credential without sending a blank secret", async () => {
    const sent = captureBody("patch", "/credentials/:id", { ...db.state.credentials[0] });
    const { user } = renderApp("/channels");
    const main = await findCredential("Main Google project");

    await user.click(main.getByRole("button", { name: "Edit Main Google project" }));
    const dialog = await findDialog("Edit Main Google project");
    expect(dialog.getByText("A secret is stored. Leave blank to keep it.")).toBeInTheDocument();
    await user.clear(dialog.getByLabelText(/^Name/));
    await user.type(dialog.getByLabelText(/^Name/), "Renamed");
    await user.click(dialog.getByRole("button", { name: "Save" }));

    await findToast(/^Updated /);
    expect(sent()).toEqual({
      name: "Renamed",
      client_id: "1234-main.apps.googleusercontent.com",
      daily_quota_units: 10_000,
    });
  });

  it("refuses to delete a credential that channels still use", async () => {
    const { user } = renderApp("/channels");
    const main = await findCredential("Main Google project");

    await user.click(main.getByRole("button", { name: "Delete Main Google project" }));
    await confirmDialog(user, "Delete credential?", "Delete credential");

    await findToast(
      "credential is used by channels: Kutty Classics, Kutty Kathaigal, Kutty Stories",
    );
    expect(db.state.credentials).toHaveLength(2);
  });

  it("keeps a credential when deleting is cancelled", async () => {
    const { user } = renderApp("/channels");
    const spare = await findCredential("Spare project");

    await user.click(spare.getByRole("button", { name: "Delete Spare project" }));
    await cancelDialog(user, "Delete credential?");

    expect(await findCredential("Spare project")).toBeTruthy();
    expect(db.state.credentials.map((c) => c.id)).toEqual(["cred-main", "cred-spare"]);
  });
});
