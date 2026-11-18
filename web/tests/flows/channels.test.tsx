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
import { failWith } from "../helpers/server";

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
