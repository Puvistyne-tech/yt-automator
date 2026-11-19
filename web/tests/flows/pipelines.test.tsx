import { screen, waitFor, within } from "@testing-library/react";
import { HttpResponse, http } from "msw";
import { db } from "@/api/mocks/db";
import { findSection } from "../helpers/editor";
import {
  cancelDialog,
  confirmDialog,
  findDialog,
  findToast,
  pathOf,
  renderApp,
} from "../helpers/renderApp";
import { failWith, server } from "../helpers/server";

async function findPipeline(name: string) {
  return within(await screen.findByRole("listitem", { name }));
}

describe("Pipelines list", () => {
  it("is reachable from the main navigation", async () => {
    const { user, router } = renderApp("/");
    const nav = within(screen.getByRole("navigation", { name: "Main" }));

    await user.click(nav.getByRole("link", { name: /Pipelines/ }));

    expect(await screen.findByRole("heading", { level: 1, name: "Pipelines" })).toBeVisible();
    expect(pathOf(router)).toBe("/pipelines");
  });

  it("shows each pipeline with its badges and how many automations use it", async () => {
    renderApp("/pipelines");

    const kids = await findPipeline("Kids story videos");
    expect(kids.getByText("Built-in")).toBeInTheDocument();
    expect(kids.getByText("For kids")).toBeInTheDocument();
    expect(kids.getByText("Used by 3 automations")).toBeInTheDocument();
    expect(kids.getByRole("link", { name: "View Kids story videos" })).toBeInTheDocument();
    expect(kids.queryByRole("button", { name: /^Delete/ })).not.toBeInTheDocument();

    const space = await findPipeline("Space facts");
    expect(space.getByText("General audience")).toBeInTheDocument();
    expect(space.getByText("Used by 1 automation")).toBeInTheDocument();
    expect(space.queryByText("Draft")).not.toBeInTheDocument();

    const history = await findPipeline("History in five minutes");
    expect(history.getByText("Draft")).toBeInTheDocument();
    expect(history.getByText("Not used by any automation")).toBeInTheDocument();
    expect(history.getByRole("link", { name: "Edit History in five minutes" })).toHaveAttribute(
      "href",
      "/pipelines/history-five",
    );
  });

  it("offers a new automation only for ready pipelines, with the type chosen", async () => {
    const { user, router } = renderApp("/pipelines");
    const history = await findPipeline("History in five minutes");
    expect(history.queryByRole("link", { name: /New automation/ })).not.toBeInTheDocument();

    const space = await findPipeline("Space facts");
    await user.click(space.getByRole("link", { name: "New automation with Space facts" }));

    const general = await findSection("General");
    expect(general.getByRole("radio", { name: /^Space facts/ })).toBeChecked();
    expect(pathOf(router)).toBe("/automations/new");
  });

  it("shows an empty state when there are no pipelines", async () => {
    server.use(http.get("/api/templates", () => HttpResponse.json([])));
    renderApp("/pipelines");

    expect(await screen.findByText("No pipelines yet")).toBeInTheDocument();
  });

  it("shows an error state with a retry when the list fails", async () => {
    failWith("get", "/templates", 500, { message: "Pipelines are unavailable." });
    renderApp("/pipelines");

    expect(await screen.findByText("Pipelines are unavailable.")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole("button", { name: "Try again" })).toBeVisible());
  });
});

async function openDialog(item: string, action: string, title: string | RegExp) {
  const app = renderApp("/pipelines");
  await app.user.click(
    (await findPipeline(item)).getByRole("button", { name: `${action} ${item}` }),
  );
  return { ...app, dialog: await findDialog(title) };
}

describe("Pipelines: duplicate", () => {
  it("copies with a new name and audience, then opens the copy", async () => {
    const { user, router, dialog } = await openDialog("Space facts", "Duplicate", /^Duplicate/);
    expect(dialog.getByRole("radio", { name: /^General audience/ })).toBeChecked();

    await user.type(dialog.getByLabelText(/^Name of the copy/), "Space for kids");
    await user.click(dialog.getByRole("radio", { name: /^For kids/ }));
    await user.click(dialog.getByRole("button", { name: "Duplicate" }));

    await findToast("Created “Space for kids”.");
    const copy = db.state.templates.find((t) => t.name === "Space for kids");
    expect(copy).toMatchObject({ audience: "kids", status: "draft", origin: "duplicate" });
    await waitFor(() => expect(pathOf(router)).toBe(`/pipelines/${copy?.id}`));
  });

  it("shows a refused name in the dialog", async () => {
    failWith("post", "/templates/:id/duplicate", 400, {
      message: "Validation failed",
      fields: { name: "name must be at most 80 characters" },
    });
    const { user, dialog } = await openDialog("Space facts", "Duplicate", /^Duplicate/);

    await user.click(dialog.getByRole("button", { name: "Duplicate" }));

    expect(await dialog.findByText("name must be at most 80 characters")).toBeInTheDocument();
    expect(db.state.templates).toHaveLength(2);
  });

  it("creates nothing when cancelled", async () => {
    const { user } = await openDialog("Space facts", "Duplicate", /^Duplicate/);

    await cancelDialog(user, /^Duplicate/);

    expect(db.state.templates).toHaveLength(2);
  });
});

describe("Pipelines: delete", () => {
  it("deletes an unused pipeline after confirming", async () => {
    const { user } = await openDialog("History in five minutes", "Delete", "Delete pipeline?");

    await confirmDialog(user, "Delete pipeline?", "Delete pipeline");

    await findToast("Deleted “History in five minutes”.");
    await waitFor(() =>
      expect(screen.queryByRole("listitem", { name: "History in five minutes" })).toBeNull(),
    );
    expect(db.state.templates.map((t) => t.id)).toEqual(["space-facts"]);
  });

  it("explains a refusal for a pipeline automations still use", async () => {
    const { user, dialog } = await openDialog("Space facts", "Delete", "Delete pipeline?");

    await user.click(dialog.getByRole("button", { name: "Delete pipeline" }));

    const alert = await dialog.findByRole("alert");
    expect(alert).toHaveTextContent("This pipeline is still in use.");
    expect(alert).toHaveTextContent("template is used by automations: Space facts weekly");
    expect(db.state.templates).toHaveLength(2);
  });

  it("reports other failures as a notification", async () => {
    failWith("delete", "/templates/:id", 500, { message: "Disk is full." });
    const { user, dialog } = await openDialog("Space facts", "Delete", "Delete pipeline?");

    await user.click(dialog.getByRole("button", { name: "Delete pipeline" }));

    await findToast("Disk is full.");
    expect(dialog.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("keeps the pipeline when deleting is cancelled", async () => {
    const { user } = await openDialog("History in five minutes", "Delete", "Delete pipeline?");

    await cancelDialog(user, "Delete pipeline?");

    expect(db.state.templates).toHaveLength(2);
  });
});
