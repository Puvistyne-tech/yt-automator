import { screen, waitFor } from "@testing-library/react";
import { db } from "@/api/mocks/db";
import {
  cancelDialog,
  confirmDialog,
  findDialog,
  findToast,
  findWithin,
  renderApp,
} from "../helpers/renderApp";
import { failWith } from "../helpers/server";

const findCard = (title: string) => findWithin(title, "section", { selector: "h2" });

async function findSecret(title: string) {
  const secrets = await findCard("Secrets");
  await secrets.findByText(title);
  return findWithin(title, "li", { selector: ".cell-title" });
}

const secret = (name: string) => db.state.secrets.find((s) => s.name === name);

describe("Secrets panel", () => {
  it("sets a secret write-only and refreshes provider availability", async () => {
    const { user } = renderApp("/providers");
    const gemini = await findSecret("Gemini API key");

    await user.click(gemini.getByRole("button", { name: "Set" }));
    const dialog = await findDialog("Set Gemini API key");
    await user.click(dialog.getByRole("button", { name: "Save secret" }));
    expect(dialog.getByLabelText(/^Value/)).toHaveAttribute("aria-invalid", "true");
    await user.type(dialog.getByLabelText(/^Value/), "AIza-secret");
    expect(dialog.getByLabelText(/^Value/)).toHaveAttribute("type", "password");
    await user.click(dialog.getByRole("button", { name: "Save secret" }));

    await findToast("Gemini API key saved.");
    expect(await gemini.findByText("Set")).toBeInTheDocument();
    const text = await findCard("LLM");
    await waitFor(() =>
      expect(text.queryByText("Secret gemini_api_key is not set.")).not.toBeInTheDocument(),
    );
  });

  it("clears a secret after confirmation", async () => {
    const { user } = renderApp("/providers");
    const pixabay = await findSecret("Pixabay API key");

    await user.click(pixabay.getByRole("button", { name: "Clear" }));
    await confirmDialog(user, "Clear secret?", "Clear secret");

    await findToast("Pixabay API key cleared.");
    expect(secret("pixabay_api_key")?.is_set).toBe(false);
  });

  it("keeps a secret when clearing is cancelled", async () => {
    const { user } = renderApp("/providers");
    const pixabay = await findSecret("Pixabay API key");

    await user.click(pixabay.getByRole("button", { name: "Clear" }));
    await cancelDialog(user, "Clear secret?");

    expect(pixabay.getByText("Set")).toBeInTheDocument();
    expect(secret("pixabay_api_key")?.is_set).toBe(true);
  });

  it("reports a failed clear and keeps the secret", async () => {
    failWith("delete", "/secrets/:name", 500, { message: "Keychain is locked." });
    const { user } = renderApp("/providers");
    const pixabay = await findSecret("Pixabay API key");

    await user.click(pixabay.getByRole("button", { name: "Clear" }));
    await confirmDialog(user, "Clear secret?", "Clear secret");

    await findToast("Keychain is locked.");
    expect(secret("pixabay_api_key")?.is_set).toBe(true);
    expect(pixabay.getByText("Set")).toBeInTheDocument();
  });

  it("keeps the set dialog open when saving fails", async () => {
    failWith("put", "/secrets/:name", 500, { message: "Keychain is locked." });
    const { user } = renderApp("/providers");
    const gemini = await findSecret("Gemini API key");

    await user.click(gemini.getByRole("button", { name: "Set" }));
    const dialog = await findDialog("Set Gemini API key");
    await user.type(dialog.getByLabelText(/^Value/), "AIza-secret");
    await user.click(dialog.getByRole("button", { name: "Save secret" }));

    await findToast("Keychain is locked.");
    expect(screen.getByRole("dialog", { name: "Set Gemini API key" })).toBeInTheDocument();
    expect(secret("gemini_api_key")?.is_set).toBe(false);
  });

  it("closes the set dialog on cancel without saving", async () => {
    const { user } = renderApp("/providers");
    const gemini = await findSecret("Gemini API key");

    await user.click(gemini.getByRole("button", { name: "Set" }));
    await cancelDialog(user, "Set Gemini API key");

    expect(secret("gemini_api_key")?.is_set).toBe(false);
  });
});
