import { screen, within } from "@testing-library/react";
import { db } from "@/api/mocks/db";
import { findToast, findWithin, renderApp } from "../helpers/renderApp";
import { failWith } from "../helpers/server";

const findCard = (title: string) => findWithin(title, "section", { selector: "h2" });

const chainIds = (capability: string) =>
  db.state.providerConfig.find((c) => c.capability === capability)?.chain.map((c) => c.provider_id);

describe("Providers page", () => {
  it("shows each chain in order with availability", async () => {
    renderApp("/providers");
    const text = await findCard("LLM");

    expect(text.getAllByRole("listitem").map((li) => li.getAttribute("aria-label"))).toEqual([
      "Ollama",
      "Google Gemini",
      "Offline fake",
    ]);
    expect(text.getByText("Secret gemini_api_key is not set.")).toBeInTheDocument();
    expect(text.getByText("Runs use Ollama, then fall back down the list.")).toBeInTheDocument();
    const narration = await findCard("TTS");
    expect(
      narration.getByText("Runs use Offline fake, then fall back down the list."),
    ).toBeInTheDocument();
  });

  it("reorders, toggles, edits options and saves the chains", async () => {
    const { user } = renderApp("/providers");
    const text = await findCard("LLM");

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
    const text = await findCard("LLM");

    await user.click(text.getByRole("button", { name: "Move Google Gemini up" }));
    await user.click(screen.getByRole("button", { name: "Save chains" }));

    await findToast("Unknown provider.");
    expect(chainIds("llm")).toEqual(["ollama", "gemini", "fake-llm"]);
  });
});
