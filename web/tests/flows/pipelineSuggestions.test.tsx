import { screen, waitFor, within } from "@testing-library/react";
import { delay, HttpResponse, http } from "msw";
import { NO_TEXT_MODEL, TEXT_MODEL_UNAVAILABLE } from "@/api/mocks/templateSuggestions";
import { disableWriters } from "../helpers/providers";
import { failWith, recordBodies, server } from "../helpers/server";
import {
  disconnectChannels,
  FIND,
  findIdea,
  findIdeas,
  onlyPlaceholderWriter,
  openSuggestions,
  PANEL,
  panel,
} from "../helpers/suggestions";

const PATH = "/templates/suggestions";

describe("Pipelines: suggest ideas", () => {
  it.each<[string, () => void, string, string | null]>([
    ["a connected channel", () => undefined, "trending on YouTube in United States", null],
    ["no connected channel", disconnectChannels, "built-in sample trends", "/channels"],
  ])(
    "lists ideas with %s and says where the trends came from",
    async (_n, arrange, source, link) => {
      arrange();
      const { user } = await openSuggestions();

      expect(await findIdeas(user)).toHaveLength(4);

      expect(panel().getByText(new RegExp(source))).toBeInTheDocument();
      const channels = panel().queryByRole("link", { name: "Connect a channel" });
      expect(channels?.getAttribute("href") ?? null).toBe(link);
      expect(panel().getByText("Written by ollama.")).toBeInTheDocument();
      expect(
        panel().getByText("1 idea was left out because it did not pass the checks."),
      ).toBeInTheDocument();
    },
  );

  it("shows each idea with its format, audience, reason and trends", async () => {
    const { user } = await openSuggestions();
    const idea = await findIdea(user, "Little sea lights");

    expect(idea.getByText("Story")).toBeInTheDocument();
    expect(idea.getByText("For kids")).toBeInTheDocument();
    expect(idea.getByText(/sea creatures that make their own light/)).toBeInTheDocument();
    expect(idea.getByText(/make calm bedtime stories/)).toBeInTheDocument();
    const trends = within(idea.getByRole("list", { name: "Trending videos it drew on" }));
    expect(trends.getAllByRole("listitem").map((item) => item.textContent)).toEqual([
      "Ocean animals that glow in the dark",
    ]);
  });

  it("sends the chosen audience, country, category and count", async () => {
    const bodies = recordBodies("post", PATH);
    const { user } = await openSuggestions();
    const form = panel();

    await user.click(form.getByRole("radio", { name: /^General audience/ }));
    await user.selectOptions(form.getByLabelText("Country"), "Another country");
    await user.type(form.getByLabelText("Country code"), "nz");
    await user.selectOptions(form.getByLabelText(/^YouTube category/), "Education");
    await user.selectOptions(form.getByLabelText("Number of ideas"), "3");
    await findIdeas(user);

    expect(bodies).toEqual([
      { engine: "narrated_video", audience: "general", region: "NZ", category: "27", count: 3 },
    ]);
    expect(panel().queryByText(/left out/)).not.toBeInTheDocument();
  });

  it.each([
    ["audience", "Who are the videos for?"],
    ["region", "Country"],
    ["category", "YouTube category (optional)"],
    ["count", "Number of ideas"],
  ])("shows a %s error on its input", async (field, label) => {
    failWith("post", PATH, 400, {
      message: "Validation failed",
      fields: { [field]: "Not right." },
    });
    const { user } = await openSuggestions();

    await user.click(panel().getByRole("button", FIND));

    const scope =
      field === "audience"
        ? panel().getByRole("group", { name: label })
        : panel().getByLabelText(label).closest(".field");
    await waitFor(() => expect(scope).toHaveTextContent("Not right."));
  });

  it("puts the server's region error on a typed country code", async () => {
    const { user } = await openSuggestions();
    await user.selectOptions(panel().getByLabelText("Country"), "Another country");
    await user.type(panel().getByLabelText("Country code"), "u");

    await user.click(panel().getByRole("button", FIND));

    await waitFor(() =>
      expect(panel().getByLabelText("Country code")).toHaveAccessibleDescription(/pattern/),
    );
  });

  it.each<[string, () => void, string]>([
    ["only a placeholder text model is ready", onlyPlaceholderWriter, NO_TEXT_MODEL],
    ["no text model is ready", disableWriters, TEXT_MODEL_UNAVAILABLE],
  ])("explains calmly when %s", async (_name, arrange, message) => {
    arrange();
    const { user } = await openSuggestions();

    await user.click(panel().getByRole("button", FIND));

    const notice = await panel().findByText(message);
    expect(notice.closest("[role=status]")).not.toBeNull();
    expect(panel().getByRole("link", { name: "Open Providers" })).toHaveAttribute(
      "href",
      "/providers",
    );
    expect(panel().queryByRole("article")).not.toBeInTheDocument();
  });

  it("shows progress and asks only once while finding ideas", async () => {
    server.use(http.post(`/api${PATH}`, () => delay("infinite")));
    const bodies = recordBodies("post", PATH);
    const { user } = await openSuggestions();
    const find = panel().getByRole("button", FIND);

    await user.click(find);
    await user.click(find);

    expect(await panel().findByRole("status", { name: "Finding ideas" })).toBeInTheDocument();
    expect(find).toBeDisabled();
    expect(bodies).toHaveLength(1);
  });

  it("says so when no pipeline template is installed", async () => {
    server.use(http.get("/api/template-engines", () => HttpResponse.json([])));
    await openSuggestions();
    expect(await panel().findByText("No pipeline templates are installed")).toBeInTheDocument();
  });

  it("closes the panel", async () => {
    const { user } = await openSuggestions();
    await user.click(panel().getByRole("button", { name: "Close" }));
    expect(screen.queryByRole("region", PANEL)).not.toBeInTheDocument();
  });
});
