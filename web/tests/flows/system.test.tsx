import { screen, waitFor, within } from "@testing-library/react";
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

const chainIds = (capability: string) =>
  db.state.providerConfig.find((c) => c.capability === capability)?.chain.map((c) => c.provider_id);

describe("Providers page", () => {
  it("shows each chain in order with availability", async () => {
    renderApp("/providers");
    const text = await findCard("Llm");

    expect(text.getAllByRole("listitem").map((li) => li.getAttribute("aria-label"))).toEqual([
      "Ollama",
      "Google Gemini",
      "Offline fake",
    ]);
    expect(text.getByText("Secret gemini_api_key is not set.")).toBeInTheDocument();
    expect(text.getByText("Runs use Ollama, then fall back down the list.")).toBeInTheDocument();
    const narration = await findCard("Tts");
    expect(
      narration.getByText("Runs use Offline fake, then fall back down the list."),
    ).toBeInTheDocument();
  });

  it("reorders, toggles, edits options and saves the chains", async () => {
    const { user } = renderApp("/providers");
    const text = await findCard("Llm");

    await user.click(text.getByRole("button", { name: "Move Offline fake up" }));
    await user.click(text.getByRole("switch", { name: "Use Ollama" }));
    const ollama = within(text.getByRole("listitem", { name: "Ollama" }));
    await user.click(ollama.getByRole("button", { name: "Options" }));
    const model = ollama.getByLabelText("Model");
    await user.clear(model);
    await user.type(model, "qwen2.5:7b");
    expect(screen.getByText("Unsaved changes")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Save chains" }));

    await findToast("Provider chains saved.");
    expect(chainIds("llm")).toEqual(["ollama", "fake-llm", "gemini"]);
    const saved = db.state.providerConfig.find((c) => c.capability === "llm")?.chain[0];
    expect(saved).toMatchObject({ enabled: false, options: { model: "qwen2.5:7b" } });
  });

  it("renders the media capability with a humanized title", async () => {
    renderApp("/providers");
    const media = await findCard("Media");

    expect(media.getByRole("listitem", { name: "FFmpeg" })).toBeInTheDocument();
  });

  it("adds and removes providers, and resets unsaved edits", async () => {
    const { user } = renderApp("/providers");
    const music = await findCard("Music");
    expect(music.getByText("No providers in this chain")).toBeInTheDocument();

    await user.selectOptions(music.getByLabelText("Add a Music provider"), "musicgen");
    expect(music.getByRole("listitem", { name: "MusicGen" })).toBeInTheDocument();
    await user.click(music.getByRole("button", { name: "Remove MusicGen" }));
    await user.selectOptions(music.getByLabelText("Add a Music provider"), "musicgen");
    await user.click(screen.getByRole("button", { name: "Reset" }));

    expect(music.getByText("No providers in this chain")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save chains" })).toBeDisabled();
  });

  it("reports a failed save", async () => {
    failWith("put", "/providers", 400, { message: "Unknown provider." });
    const { user } = renderApp("/providers");
    const text = await findCard("Llm");

    await user.click(text.getByRole("button", { name: "Move Google Gemini up" }));
    await user.click(screen.getByRole("button", { name: "Save chains" }));

    await findToast("Unknown provider.");
    expect(chainIds("llm")).toEqual(["ollama", "gemini", "fake-llm"]);
  });
});

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
    const text = await findCard("Llm");
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

describe("Settings page", () => {
  it("validates and saves app settings", async () => {
    const { user } = renderApp("/settings");
    const parallel = await screen.findByLabelText(/^Parallel runs/);
    expect(
      screen.getByDisplayValue("~/Library/Application Support/YouTube Automator"),
    ).toHaveAttribute("readonly");

    await user.clear(parallel);
    await user.click(screen.getByRole("button", { name: "Save settings" }));
    expect(screen.getByText("Use a whole number, at least 1.")).toBeInTheDocument();

    await user.type(parallel, "3");
    await user.selectOptions(screen.getByLabelText(/^Timezone/), "UTC");
    await user.click(screen.getByRole("button", { name: "Save settings" }));

    await findToast("Settings saved.");
    expect(db.state.settings).toMatchObject({ max_parallel_runs: 3, timezone: "UTC" });
  });

  it("shows server field errors on the matching setting", async () => {
    failWith("put", "/settings", 400, {
      message: "The settings are not valid.",
      fields: { "body.timezone": "Unknown timezone." },
    });
    const { user } = renderApp("/settings");
    await user.selectOptions(await screen.findByLabelText(/^Timezone/), "UTC");
    await user.click(screen.getByRole("button", { name: "Save settings" }));

    await findToast("The settings are not valid.");
    expect(screen.getByText("Unknown timezone.")).toBeInTheDocument();
    expect(screen.getByLabelText(/^Timezone/)).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByText("Unsaved changes")).toBeInTheDocument();
  });
});

describe("Dashboard", () => {
  it("summarizes automations, review queue, recent runs and quota", async () => {
    renderApp("/");

    const review = await findCard("Waiting for your review");
    expect(await review.findByText("Bedtime stories")).toBeInTheDocument();
    const recent = await screen.findByRole("table", { name: "Recent runs" });
    expect(within(recent).getAllByRole("row")).toHaveLength(6);
    const quota = await findCard("YouTube quota today");
    expect(quota.getByText("Main Google project")).toBeInTheDocument();
    expect(
      screen.getByText("Awaiting review", { selector: ".stat-label" }).closest(".stat-card"),
    ).toHaveTextContent("1");
  });

  it("shows an all caught up state with nothing to review", async () => {
    db.state.runs = db.state.runs.filter((r) => r.status !== "awaiting_review");
    renderApp("/");

    expect(await screen.findByText("All caught up")).toBeInTheDocument();
  });
});
