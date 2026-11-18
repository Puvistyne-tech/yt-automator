import { screen, waitFor, within } from "@testing-library/react";
import { db } from "@/api/mocks/db";
import { findDialog, findRow, findToast, pathOf, renderApp } from "../helpers/renderApp";

async function findCredential(name: string) {
  const title = await screen.findByText(name, { selector: ".cell-title" });
  const item = title.closest("li");
  if (item === null) {
    throw new Error(`No credential ${name}`);
  }
  return within(item);
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

    await waitFor(() => expect(navigateExternal).toHaveBeenCalledTimes(1));
    expect(navigateExternal.mock.calls[0]?.[0]).toMatch(/credential=cred-main/);
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

  it("adds a credential after validating the secret", async () => {
    const { user } = renderApp("/channels");
    await findCredential("Main Google project");

    await user.click(screen.getAllByRole("button", { name: "Add credential" })[0] as HTMLElement);
    const dialog = await findDialog("Add Google API credential");
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

  it("refuses to delete a credential that channels still use", async () => {
    const { user } = renderApp("/channels");
    const main = await findCredential("Main Google project");

    await user.click(main.getByRole("button", { name: "Delete Main Google project" }));
    await user.click(
      (await findDialog("Delete credential?")).getByRole("button", { name: "Delete credential" }),
    );

    await findToast("Disconnect the channels using this credential first.");
    expect(db.state.credentials).toHaveLength(2);
  });

  it("edits a channel's upload defaults", async () => {
    const { user } = renderApp("/channels");
    const row = await findRow("Channels", "Kutty Stories");

    await user.click(row.getByRole("button", { name: "Defaults" }));
    const dialog = await findDialog("Upload defaults for Kutty Stories");
    await user.selectOptions(dialog.getByLabelText("Privacy"), "unlisted");
    await user.click(dialog.getByRole("switch", { name: "Notify subscribers on upload" }));
    await user.click(dialog.getByRole("button", { name: "Save defaults" }));

    await findToast("Saved defaults for Kutty Stories.");
    expect(db.state.channels[0]?.defaults).toMatchObject({
      privacy: "unlisted",
      notify_subscribers: true,
    });
  });

  it("disconnects a channel after confirmation and reports conflicts", async () => {
    const { user } = renderApp("/channels");
    const row = await findRow("Channels", "Kutty Stories");

    await user.click(row.getByRole("button", { name: "Disconnect Kutty Stories" }));
    await user.click(
      (await findDialog("Disconnect channel?")).getByRole("button", { name: "Disconnect" }),
    );
    await findToast("An enabled automation still publishes to this channel.");

    db.state.automations = [];
    await user.click(row.getByRole("button", { name: "Disconnect Kutty Stories" }));
    await user.click(
      (await findDialog("Disconnect channel?")).getByRole("button", { name: "Disconnect" }),
    );
    await findToast("Disconnected Kutty Stories.");
    expect(db.state.channels.map((c) => c.id)).toEqual(["chan-ta"]);
  });
});
