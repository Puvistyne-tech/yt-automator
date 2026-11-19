import { screen, waitFor, within } from "@testing-library/react";
import { delay, http } from "msw";
import { db } from "@/api/mocks/db";
import { newPipelineState } from "@/api/paths";
import type { TemplateInput } from "@/api/types";
import { findToast, pathOf, renderApp } from "../helpers/renderApp";
import { failWith, recordBodies, server } from "../helpers/server";
import { findIdea, openSuggestions } from "../helpers/suggestions";

const IDEA: TemplateInput = {
  engine: "narrated_video",
  name: "Sky science quiz",
  description: "Test what you know about light.",
  audience: "general",
  status: "draft",
  origin: "suggested",
  definition: { structure: "quiz", brief: "Five questions about light in nature." },
};

const stored = (name: string) => db.state.templates.find((t) => t.name === name);

function expectPrefilled() {
  expect(screen.getByLabelText(/^Name/)).toHaveValue("Sky science quiz");
  expect(screen.getByLabelText(/^What the videos are about/)).toHaveValue(
    "Five questions about light in nature.",
  );
  expect(screen.getByRole("combobox", { name: "Format" })).toHaveDisplayValue("Quiz");
  expect(screen.getByText("General audience")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Simple", pressed: true })).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Continue" })).not.toBeInTheDocument();
}

describe("Pipelines: use a suggested idea", () => {
  it("opens the new-pipeline form prefilled and saves nothing until Save", async () => {
    const { user, router } = await openSuggestions();
    const idea = await findIdea(user, "Little sea lights");

    await user.click(idea.getByRole("button", { name: "Use this idea" }));

    await waitFor(() => expect(pathOf(router)).toBe("/pipelines/new"));
    expect(await screen.findByLabelText(/^Name/)).toHaveValue("Little sea lights");
    expect(screen.getByRole("region", { name: "Try a sample script" })).toBeInTheDocument();
    expect(db.state.templates).toHaveLength(2);

    await user.click(screen.getByRole("button", { name: "Save as draft" }));

    await findToast("Saved “Little sea lights”.");
    expect(stored("Little sea lights")).toMatchObject({
      audience: "kids",
      status: "draft",
      origin: "suggested",
    });
  });

  it("opens a prefilled draft passed in the route state", async () => {
    renderApp({ pathname: "/pipelines/new", state: newPipelineState(IDEA) });
    await screen.findByLabelText(/^Name/);
    expectPrefilled();
  });

  it("opens a prefilled draft whose definition has values of the wrong type", async () => {
    const definition = { structure: "quiz", topics: "planets", length: 3, tone: ["calm"] };
    renderApp({ pathname: "/pipelines/new", state: newPipelineState({ ...IDEA, definition }) });

    expect(await screen.findByLabelText(/^Name/)).toHaveValue("Sky science quiz");
    expect(screen.getByRole("combobox", { name: "Format" })).toHaveDisplayValue("Quiz");
    expect(screen.getByRole("region", { name: "Try a sample script" })).toBeInTheDocument();
  });

  it.each([
    ["no state, as after a refresh", null],
    ["a state that is not a draft", { prefill: { name: 3 } }],
    ["a draft for an engine that is not installed", newPipelineState({ ...IDEA, engine: "x" })],
  ])("falls back to the blank flow with %s", async (_name, state) => {
    renderApp({ pathname: "/pipelines/new", state });
    expect(await screen.findByText(/cannot be changed later/)).toBeInTheDocument();
    expect(screen.queryByLabelText(/^Name/)).not.toBeInTheDocument();
  });
});

describe("Pipelines: save a suggested idea as a draft", () => {
  it("creates a suggested draft and refreshes the list", async () => {
    const { user } = await openSuggestions();
    const idea = await findIdea(user, "Little sea lights");

    await user.click(idea.getByRole("button", { name: "Save as draft" }));

    await findToast("Saved “Little sea lights” as a draft.");
    expect(stored("Little sea lights")).toMatchObject({ origin: "suggested", status: "draft" });
    const item = within(await screen.findByRole("listitem", { name: "Little sea lights" }));
    expect(item.getByText("Draft")).toBeInTheDocument();
    expect(idea.getByRole("link", { name: "Open Little sea lights" })).toHaveAttribute(
      "href",
      `/pipelines/${stored("Little sea lights")?.id}`,
    );
  });

  it.each<[number, Parameters<typeof failWith>[3]]>([
    [500, { message: "Disk is full." }],
    [
      400,
      {
        message: "name must be at most 80 characters",
        fields: { name: "name must be at most 80 characters" },
      },
    ],
    [409, { code: "template_type_taken", message: "pipeline type 't_x' already exists" }],
  ])("reports a %i save failure as a notification", async (status, body) => {
    failWith("post", "/templates", status, body);
    const { user } = await openSuggestions();
    const idea = await findIdea(user, "Little sea lights");

    await user.click(idea.getByRole("button", { name: "Save as draft" }));

    await findToast(body.message);
    expect(idea.getByRole("button", { name: "Save as draft" })).toBeEnabled();
    expect(screen.queryByRole("listitem", { name: "Little sea lights" })).toBeNull();
    expect(db.state.templates).toHaveLength(2);
  });

  it("creates only one draft on a double click", async () => {
    server.use(http.post("/api/templates", () => delay("infinite")));
    const bodies = recordBodies("post", "/templates");
    const { user } = await openSuggestions();
    const idea = await findIdea(user, "Little sea lights");
    const save = idea.getByRole("button", { name: "Save as draft" });

    await user.click(save);
    await user.click(save);

    expect(save).toBeDisabled();
    expect(bodies).toHaveLength(1);
  });
});
