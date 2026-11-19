import { screen, waitFor } from "@testing-library/react";
import { delay, HttpResponse, http } from "msw";
import { db } from "@/api/mocks/db";
import { findToast, pathOf, renderApp, type User } from "../helpers/renderApp";
import { failWith, server } from "../helpers/server";

const stored = (name: string) => db.state.templates.find((t) => t.name === name);

async function startNew(audience: "For kids" | "General audience") {
  const app = renderApp("/pipelines/new");
  expect(await screen.findByText(/cannot be changed later/)).toBeInTheDocument();
  await app.user.click(screen.getByRole("radio", { name: new RegExp(`^${audience}`) }));
  await app.user.click(screen.getByRole("button", { name: "Continue" }));
  await screen.findByLabelText(/^What the videos are about/);
  return app;
}

async function fillBasics(user: User, name: string, brief: string) {
  await user.type(screen.getByLabelText(/^Name/), name);
  await user.type(screen.getByLabelText(/^What the videos are about/), brief);
}

describe("Pipeline editor: create", () => {
  it("creates a kids pipeline as a draft from the kids blank", async () => {
    const { user, router } = await startNew("For kids");
    expect(screen.getByRole("combobox", { name: "Format" })).toHaveDisplayValue("Story");
    expect(screen.getByText("For kids")).toBeInTheDocument();

    await fillBasics(user, "Animal friends", "Short stories about animals helping each other.");
    await user.click(screen.getByRole("button", { name: "Save as draft" }));

    await findToast("Saved “Animal friends”.");
    const saved = stored("Animal friends");
    expect(saved).toMatchObject({ audience: "kids", status: "draft", origin: "blank" });
    expect(saved?.definition).toMatchObject({
      structure: "story",
      brief: "Short stories about animals helping each other.",
    });
    await waitFor(() => expect(pathOf(router)).toBe(`/pipelines/${saved?.id}`));
  });

  it("creates a general pipeline and makes it ready", async () => {
    const { user } = await startNew("General audience");

    await fillBasics(user, "Ocean wonders", "Facts about the sea.");
    await user.click(screen.getByRole("button", { name: "Save and make ready" }));

    await findToast("Saved “Ocean wonders”.");
    expect(stored("Ocean wonders")).toMatchObject({ audience: "general", status: "ready" });
    expect(stored("Ocean wonders")?.definition).toMatchObject({ brief: "Facts about the sea." });
  });

  it("asks for a name before saving and shows server errors at their fields", async () => {
    const { user } = await startNew("General audience");
    await user.click(screen.getByRole("button", { name: "Save as draft" }));
    expect(await screen.findByText("Give the pipeline a name.")).toBeInTheDocument();

    failWith("post", "/templates", 400, {
      message: "Validation failed",
      fields: { "definition.brief": "The brief speaks to children." },
    });
    await user.type(screen.getByLabelText(/^Name/), "Bad brief");
    await user.click(screen.getByRole("button", { name: "Save as draft" }));

    await findToast("Validation failed");
    expect(screen.getByLabelText(/^What the videos are about/)).toHaveAccessibleDescription(
      /The brief speaks to children/,
    );
    expect(stored("Bad brief")).toBeUndefined();
  });

  it("refuses a name over 80 characters without sending it", async () => {
    const sent = vi.fn();
    server.events.on("request:start", sent);
    const { user } = await startNew("General audience");
    sent.mockClear();

    await user.type(screen.getByLabelText(/^Name/), "x".repeat(81));
    await user.click(screen.getByRole("button", { name: "Save as draft" }));

    expect(await screen.findByText("Keep the name to 80 characters or fewer.")).toBeVisible();
    expect(sent).not.toHaveBeenCalled();
    server.events.removeListener("request:start", sent);
  });

  it("keeps the form and shows the conflict when the type is taken", async () => {
    failWith("post", "/templates", 409, {
      code: "template_type_taken",
      message: "pipeline type 't_x' already exists",
    });
    const { user } = await startNew("General audience");
    await user.type(screen.getByLabelText(/^Name/), "Taken");
    await user.click(screen.getByRole("button", { name: "Save as draft" }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("That pipeline type already exists.");
    expect(alert).toHaveTextContent("pipeline type 't_x' already exists");
    expect(screen.getByLabelText(/^Name/)).toHaveValue("Taken");
  });

  it("does not show the form until an audience is chosen", async () => {
    renderApp("/pipelines/new");

    expect(await screen.findByRole("button", { name: "Continue" })).toBeDisabled();
    expect(screen.queryByLabelText(/^What the videos are about/)).not.toBeInTheDocument();
  });
});

describe("Pipeline editor: edit", () => {
  it("edits a saved pipeline and shows its audience and revision", async () => {
    const { user } = renderApp("/pipelines/space-facts");
    const name = await screen.findByLabelText(/^Name/);
    expect(name).toHaveValue("Space facts");
    expect(screen.getByText("Revision 3")).toBeInTheDocument();
    expect(screen.getByText("General audience")).toBeInTheDocument();

    await user.type(name, " daily");
    await user.click(screen.getByRole("button", { name: "Save changes" }));

    await findToast("Saved “Space facts daily”.");
    expect(stored("Space facts daily")).toMatchObject({ revision: 4, status: "ready" });
    expect(screen.queryByRole("radio", { name: /^For kids/ })).not.toBeInTheDocument();
    expect(await screen.findByText("Revision 4")).toBeInTheDocument();
  });

  it("makes a draft ready with the status switch", async () => {
    const { user } = renderApp("/pipelines/history-five");
    const ready = await screen.findByRole("switch", { name: /Ready to use/ });
    expect(ready).not.toBeChecked();

    await user.click(ready);
    await user.click(screen.getByRole("button", { name: "Save changes" }));

    await findToast("Saved “History in five minutes”.");
    expect(stored("History in five minutes")?.status).toBe("ready");
  });

  it("explains why a pipeline in use cannot go back to draft", async () => {
    const { user } = renderApp("/pipelines/space-facts");
    await user.click(await screen.findByRole("switch", { name: /Ready to use/ }));
    await user.click(screen.getByRole("button", { name: "Save changes" }));

    const alert = await screen.findByText(/This pipeline is still in use/);
    expect(alert.closest("[role=alert]")).toHaveTextContent(
      "template is used by automations: Space facts weekly",
    );
    expect(stored("Space facts")?.status).toBe("ready");
  });

  it("shows a not found state for an unknown pipeline", async () => {
    renderApp("/pipelines/missing");

    expect(await screen.findByText("Pipeline not found")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Back to pipelines" })).toBeInTheDocument();
  });
});

describe("Pipeline editor: loading problems", () => {
  it.each(["/template-engines", "/templates/:id"])(
    "shows a loading state while %s loads",
    async (path) => {
      server.use(http.get(`/api${path}`, () => delay("infinite")));
      renderApp("/pipelines/space-facts");

      expect(await screen.findByRole("status", { name: "Loading pipeline" })).toBeVisible();
      expect(screen.queryByLabelText(/^Name/)).not.toBeInTheDocument();
    },
  );

  it.each(["/pipelines/new", "/pipelines/space-facts"])(
    "says so when the template engine is not installed at %s",
    async (route) => {
      server.use(http.get("/api/template-engines", () => HttpResponse.json([])));
      renderApp(route);

      expect(await screen.findByText(/is not installed/)).toBeInTheDocument();
    },
  );

  it.each([
    ["/template-engines", "Engines are unavailable."],
    ["/templates/:id", "The pipeline could not be read."],
  ])("shows an error with a retry when %s fails", async (path, message) => {
    failWith("get", path, 500, { message });
    renderApp("/pipelines/space-facts");

    expect(await screen.findByText(message)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
  });
});

describe("Pipeline editor: built-in", () => {
  it("opens read-only and duplicates to customise", async () => {
    const { user, router } = renderApp("/pipelines/kids_story");
    expect(await screen.findByText(/Built-in pipelines cannot be changed/)).toBeInTheDocument();
    expect(screen.getByLabelText(/^What the videos are about/)).toBeDisabled();
    expect(screen.queryByRole("button", { name: "Save changes" })).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Duplicate to customise" }));
    await user.click(await screen.findByRole("button", { name: "Duplicate" }));

    await findToast("Created “Kids story videos (copy)”.");
    const copy = stored("Kids story videos (copy)");
    expect(copy).toMatchObject({ audience: "kids", status: "draft", origin: "duplicate" });
    await waitFor(() => expect(pathOf(router)).toBe(`/pipelines/${copy?.id}`));
    expect(await screen.findByLabelText(/^Name/)).toHaveValue("Kids story videos (copy)");
  });
});
