import { screen, waitFor } from "@testing-library/react";
import { HttpResponse, http } from "msw";
import { db } from "@/api/mocks/db";
import { findToast, pathOf, renderApp, type User } from "../helpers/renderApp";
import { failWith, server } from "../helpers/server";

const stored = (name: string) => db.state.templates.find((t) => t.name === name);

async function startNew(audience: "For kids" | "General audience") {
  const app = renderApp("/pipelines/new");
  expect(await screen.findByText(/cannot be changed later/)).toBeInTheDocument();
  await app.user.click(screen.getByRole("radio", { name: new RegExp(`^${audience}`) }));
  await app.user.click(screen.getByRole("button", { name: "Continue" }));
  await screen.findByLabelText(/^Brief/);
  return app;
}

async function fillBasics(user: User, name: string, brief: string) {
  await user.type(screen.getByLabelText(/^Name/), name);
  await user.type(screen.getByLabelText(/^Brief/), brief);
}

describe("Pipeline editor: create", () => {
  it("creates a kids pipeline as a draft from the kids blank", async () => {
    const { user, router } = await startNew("For kids");
    expect(screen.getByLabelText("Structure")).toHaveDisplayValue("Story with characters");
    expect(screen.getByText("For kids")).toBeInTheDocument();

    await fillBasics(user, "Animal friends", "Short stories about animals helping each other.");
    await user.click(screen.getByRole("button", { name: "Save as draft" }));

    await findToast("Saved “Animal friends”.");
    const saved = stored("Animal friends");
    expect(saved).toMatchObject({ audience: "kids", status: "draft", origin: "blank" });
    expect(saved?.definition).toMatchObject({ structure: "story", tone: "calm" });
    await waitFor(() => expect(pathOf(router)).toBe(`/pipelines/${saved?.id}`));
  });

  it("creates a general pipeline and makes it ready", async () => {
    const { user } = await startNew("General audience");

    await fillBasics(user, "Ocean wonders", "Facts about the sea.");
    await user.click(screen.getByRole("button", { name: "Save and make ready" }));

    await findToast("Saved “Ocean wonders”.");
    expect(stored("Ocean wonders")).toMatchObject({ audience: "general", status: "ready" });
    expect(stored("Ocean wonders")?.definition).toMatchObject({ structure: "explainer" });
  });

  it("asks for a name before saving and shows server errors at their fields", async () => {
    const { user } = await startNew("General audience");
    await user.click(screen.getByRole("button", { name: "Save as draft" }));
    expect(await screen.findByText("Give the pipeline a name.")).toBeInTheDocument();

    await user.type(screen.getByLabelText(/^Name/), "No brief");
    await user.click(screen.getByRole("button", { name: "Save as draft" }));

    await findToast("Validation failed");
    expect(screen.getByLabelText(/^Brief/)).toHaveAccessibleDescription(
      /Describe what the videos are about/,
    );
    expect(stored("No brief")).toBeUndefined();
  });

  it("does not show the form until an audience is chosen", async () => {
    renderApp("/pipelines/new");

    expect(await screen.findByRole("button", { name: "Continue" })).toBeDisabled();
    expect(screen.queryByLabelText(/^Brief/)).not.toBeInTheDocument();
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
    expect(stored("Space facts daily")?.revision).toBe(4);
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
    expect(screen.getByLabelText(/^Brief/)).toBeDisabled();
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
