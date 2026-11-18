import { screen } from "@testing-library/react";
import { HttpResponse, http } from "msw";
import { kidsStoryPipeline } from "@/api/mocks/fixtures/pipeline";
import { findSection, sectionByName, targetRow } from "../helpers/editor";
import { renderApp } from "../helpers/renderApp";
import { failWith, server } from "../helpers/server";

describe("Automation editor: warnings and server errors", () => {
  it("explains that no pipeline types are installed", async () => {
    server.use(http.get("/api/pipelines", () => HttpResponse.json([])));
    renderApp("/automations/new");
    await findSection("General");

    expect(
      await screen.findByText(
        "No pipeline types are installed, so there is nothing to automate yet.",
      ),
    ).toBeInTheDocument();
  });

  it("warns when a target's channel needs reconnecting", async () => {
    renderApp("/automations/auto-festival");
    await findSection("Targets");

    expect(
      targetRow(1).getByText(
        "Story Classics needs reconnecting on the Channels page before runs can publish to it.",
      ),
    ).toBeInTheDocument();
  });

  it("shows server errors on nested language and output positions", async () => {
    failWith("put", "/automations/auto-bedtime", 400, {
      code: "validation_failed",
      message: "Validation failed",
      fields: {
        "languages.1": "pipeline does not offer language 'xx'",
        "targets.0.variants.1": "pipeline does not offer 'wide'",
        "targets.0.made_for_kids": "kids content must be made for kids",
        "targets.0.privacy": "privacy is not allowed",
        "targets.0.playlist_id": "playlist not found",
      },
    });
    const { user } = renderApp("/automations/auto-bedtime");
    const general = await findSection("General");
    await user.type(general.getByLabelText(/^Name/), "!");
    await user.click(screen.getByRole("button", { name: "Save changes" }));

    expect(
      await sectionByName("Languages").findByText("pipeline does not offer language 'xx'"),
    ).toBeInTheDocument();
    expect(targetRow(1).getByText("pipeline does not offer 'wide'")).toBeInTheDocument();
    expect(targetRow(1).getByText("kids content must be made for kids")).toBeInTheDocument();
    expect(targetRow(1).getByText("privacy is not allowed")).toBeInTheDocument();
    expect(targetRow(1).getByText("playlist not found")).toBeInTheDocument();
  });

  it("shows a made for kids error on a pipeline without the kids lock", async () => {
    const open = { ...kidsStoryPipeline, capabilities: [] };
    server.use(
      http.get("/api/pipelines", () => HttpResponse.json([open])),
      http.get("/api/pipelines/:typeId", () => HttpResponse.json(open)),
    );
    failWith("put", "/automations/auto-bedtime", 400, {
      code: "validation_failed",
      message: "Validation failed",
      fields: { "targets.0.made_for_kids": "choose yes or no" },
    });
    const { user } = renderApp("/automations/auto-bedtime");
    const general = await findSection("General");
    expect(targetRow(1).queryByText(/needs reconnecting/)).not.toBeInTheDocument();
    await user.type(general.getByLabelText(/^Name/), "!");
    await user.click(screen.getByRole("button", { name: "Save changes" }));

    expect(await targetRow(1).findByText("choose yes or no")).toBeInTheDocument();
    expect(targetRow(1).getByRole("combobox", { name: /Made for kids/ })).toBeInTheDocument();
  });
});
