import { screen, waitFor } from "@testing-library/react";
import { db } from "@/api/mocks/db";
import {
  cancelDialog,
  confirmDialog,
  findDialog,
  findRow,
  findToast,
  findWithin,
  pathOf,
  renderApp,
} from "../helpers/renderApp";
import { captureBody, failWith } from "../helpers/server";

const findCredential = (name: string) => findWithin(name, "li", { selector: ".cell-title" });
const channel = (id: string) => db.state.channels.find((c) => c.id === id);

async function openDefaults(title: string) {
  const app = renderApp("/channels");
  const row = await findRow("Channels", title);
  await app.user.click(row.getByRole("button", { name: "Defaults" }));
  return { ...app, dialog: await findDialog(`Upload defaults for ${title}`) };
}

describe("Channels page", () => {
  it("lists credentials with quota and secret state, and connected channels", async () => {
    renderApp("/channels");

    const main = await findCredential("Main Google project");
    expect(main.getByText("Secret stored")).toBeInTheDocument();
    expect(main.getByText("3,250 / 10,000")).toBeInTheDocument();
    const spare = await findCredential("Spare project");
    expect(spare.getByText("No secret")).toBeInTheDocument();
    expect(spare.getByRole("button", { name: "Connect channel" })).toBeDisabled();
    const row = await findRow("Channels", "Kutty Kathaigal");
    expect(row.getByText("Unlisted")).toBeInTheDocument();
    expect(row.getByText("Main Google project")).toBeInTheDocument();
  });

  it("connects a channel by sending the browser to the authorization url", async () => {
    const { user, navigateExternal } = renderApp("/channels");
    const main = await findCredential("Main Google project");

    await user.click(main.getByRole("button", { name: "Connect channel" }));

    await waitFor(() =>
      expect(navigateExternal).toHaveBeenCalledWith(
        expect.stringContaining("credential=cred-main"),
      ),
    );
  });

  it("reports a connect flow that cannot start", async () => {
    failWith("post", "/channels/connect", 502, { message: "Google is unreachable." });
    const { user, navigateExternal } = renderApp("/channels");
    const main = await findCredential("Main Google project");

    await user.click(main.getByRole("button", { name: "Connect channel" }));

    await findToast("Google is unreachable.");
    expect(navigateExternal).not.toHaveBeenCalled();
  });

  it.each([
    ["?connected=chan-ta", "Connected Kutty Kathaigal."],
    ["?error=access_denied", "Connecting the channel failed: access denied."],
  ])("shows a toast when returning with %s and cleans the url", async (query, message) => {
    const { router } = renderApp(`/channels${query}`);

    await findToast(message);
    await waitFor(() => expect(router.state.location.search).toBe(""));
    expect(pathOf(router)).toBe("/channels");
  });
});

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

    await findToast("Disconnect the channels using this credential first.");
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

describe("Channel defaults and disconnect", () => {
  it("edits a channel's upload defaults", async () => {
    const { user, dialog } = await openDefaults("Kutty Stories");

    await user.selectOptions(dialog.getByLabelText("Privacy"), "unlisted");
    await user.click(dialog.getByRole("switch", { name: "Notify subscribers on upload" }));
    await user.click(dialog.getByRole("button", { name: "Save defaults" }));

    await findToast("Saved defaults for Kutty Stories.");
    expect(channel("chan-en")?.defaults).toMatchObject({
      privacy: "unlisted",
      notify_subscribers: true,
    });
  });

  it("keeps the dialog open when saving defaults fails", async () => {
    failWith("patch", "/channels/:id", 502, { message: "YouTube rejected the category." });
    const { user, dialog } = await openDefaults("Kutty Stories");

    await user.selectOptions(dialog.getByLabelText("Privacy"), "public");
    await user.click(dialog.getByRole("button", { name: "Save defaults" }));

    await findToast("YouTube rejected the category.");
    expect(screen.getByRole("dialog", { name: "Upload defaults for Kutty Stories" })).toBeVisible();
    expect(channel("chan-en")?.defaults.privacy).toBe("private");
  });

  it("disconnects a channel after confirmation and reports conflicts", async () => {
    const { user } = renderApp("/channels");
    const row = await findRow("Channels", "Kutty Stories");

    await user.click(row.getByRole("button", { name: "Disconnect Kutty Stories" }));
    await confirmDialog(user, "Disconnect channel?", "Disconnect");
    await findToast("An enabled automation still publishes to this channel.");

    db.state.automations = [];
    await user.click(row.getByRole("button", { name: "Disconnect Kutty Stories" }));
    await confirmDialog(user, "Disconnect channel?", "Disconnect");
    await findToast("Disconnected Kutty Stories.");
    expect(db.state.channels.map((c) => c.id)).toEqual(["chan-ta"]);
  });

  it("keeps a channel when disconnecting is cancelled", async () => {
    const { user } = renderApp("/channels");
    const row = await findRow("Channels", "Kutty Stories");

    await user.click(row.getByRole("button", { name: "Disconnect Kutty Stories" }));
    await cancelDialog(user, "Disconnect channel?");

    expect(row.getByText("Kutty Stories")).toBeInTheDocument();
    expect(db.state.channels.map((c) => c.id)).toEqual(["chan-en", "chan-ta"]);
  });
});
