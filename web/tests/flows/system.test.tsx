import { screen, waitFor, within } from "@testing-library/react";
import { db } from "@/api/mocks/db";
import { findDialog, findToast, renderApp } from "../helpers/renderApp";
import { failWith } from "../helpers/server";

async function findCard(title: string) {
  const heading = await screen.findByRole("heading", { level: 2, name: title });
  const card = heading.closest("section");
  if (card === null) {
    throw new Error(`No card ${title}`);
  }
  return within(card);
}

const chainIds = (capability: string) =>
  db.state.providerConfig.find((c) => c.capability === capability)?.chain.map((c) => c.provider_id);

describe("Providers page", () => {
  it("shows each chain in order with availability", async () => {
    renderApp("/providers");
    const text = await findCard("Text generation");

    expect(text.getAllByRole("listitem").map((li) => li.getAttribute("aria-label"))).toEqual([
      "Ollama",
      "Google Gemini",
      "Offline fake",
    ]);
    expect(text.getByText("Secret gemini_api_key is not set.")).toBeInTheDocument();
    expect(text.getByText("Runs use Ollama, then fall back down the list.")).toBeInTheDocument();
    const narration = await findCard("Narration");
    expect(
      narration.getByText("Runs use Offline fake, then fall back down the list."),
    ).toBeInTheDocument();
  });

  it("reorders, toggles, edits options and saves the chains", async () => {
    const { user } = renderApp("/providers");
    const text = await findCard("Text generation");

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
    const text = await findCard("Text generation");

    await user.click(text.getByRole("button", { name: "Move Google Gemini up" }));
    await user.click(screen.getByRole("button", { name: "Save chains" }));

    await findToast("Unknown provider.");
    expect(chainIds("llm")).toEqual(["ollama", "gemini", "fake-llm"]);
  });
});

describe("Secrets panel", () => {
  it("sets a secret write-only and refreshes provider availability", async () => {
    const { user } = renderApp("/providers");
    const secrets = await findCard("Secrets");
    const gemini = within(
      (await secrets.findByText("Gemini API key")).closest("li") as HTMLElement,
    );

    await user.click(gemini.getByRole("button", { name: "Set" }));
    const dialog = await findDialog("Set Gemini API key");
    await user.click(dialog.getByRole("button", { name: "Save secret" }));
    expect(dialog.getByLabelText(/^Value/)).toHaveAttribute("aria-invalid", "true");
    await user.type(dialog.getByLabelText(/^Value/), "AIza-secret");
    expect(dialog.getByLabelText(/^Value/)).toHaveAttribute("type", "password");
    await user.click(dialog.getByRole("button", { name: "Save secret" }));

    await findToast("Gemini API key saved.");
    expect(await gemini.findByText("Set")).toBeInTheDocument();
    const text = await findCard("Text generation");
    await waitFor(() =>
      expect(text.queryByText("Secret gemini_api_key is not set.")).not.toBeInTheDocument(),
    );
  });

  it("clears a secret after confirmation", async () => {
    const { user } = renderApp("/providers");
    const secrets = await findCard("Secrets");
    const pixabay = within(
      (await secrets.findByText("Pixabay API key")).closest("li") as HTMLElement,
    );

    await user.click(pixabay.getByRole("button", { name: "Clear" }));
    await user.click(
      (await findDialog("Clear secret?")).getByRole("button", { name: "Clear secret" }),
    );

    await findToast("Pixabay API key cleared.");
    expect(db.state.secrets.find((s) => s.name === "pixabay_api_key")?.is_set).toBe(false);
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
