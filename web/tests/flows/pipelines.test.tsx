import { screen, waitFor, within } from "@testing-library/react";
import { HttpResponse, http } from "msw";
import { findSection } from "../helpers/editor";
import { pathOf, renderApp } from "../helpers/renderApp";
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
