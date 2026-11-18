import { screen, within } from "@testing-library/react";
import { db } from "@/api/mocks/db";
import { artifactsFor, STORY_ARTIFACT, WORKING_ARTIFACTS } from "@/api/mocks/fixtures/artifacts";
import type { Artifact } from "@/api/types";
import { openRun } from "../helpers/runs";

function withArtifacts(artifacts: Artifact[]) {
  db.state.runs = db.state.runs.map((r) => (r.id === "run-review" ? { ...r, artifacts } : r));
}

const region = (name: string) => within(screen.getByRole("region", { name }));

function stageSummaries(container: HTMLElement): [string, string][] {
  return [...container.querySelectorAll("summary")].map((summary) => [
    summary.children[0]?.textContent ?? "",
    summary.children[1]?.textContent ?? "",
  ]);
}

describe("Run artifacts", () => {
  it("lists final outputs before intermediate files grouped by stage", async () => {
    await openRun("run-review");

    const sections = screen.getAllByRole("region", { name: /Final outputs|Intermediate files/ });
    expect(sections.map((s) => s.getAttribute("aria-label"))).toEqual([
      "Final outputs",
      "Intermediate files",
    ]);
    expect(await region("Final outputs").findByText("English — Episode · 16:9")).toBeVisible();
    expect(region("Final outputs").queryByText("story.md")).not.toBeInTheDocument();
    expect(stageSummaries(screen.getByRole("region", { name: "Intermediate files" }))).toEqual([
      ["Write story", "1 file"],
      ["Illustrate scenes", "3 files"],
      ["Animate", "1 file"],
      ["Narrate", "2 files"],
    ]);
  });

  it("shows a stage's files only while it is open", async () => {
    const { user } = await openRun("run-review");
    const working = region("Intermediate files");
    expect(working.queryByText("story.md")).not.toBeInTheDocument();

    await user.click(working.getByText("Write story"));
    expect(await working.findByText("story.md")).toBeInTheDocument();
    expect(working.queryByText("scene-1.svg")).not.toBeInTheDocument();

    await user.click(working.getByText("Write story"));
    expect(working.queryByText("story.md")).not.toBeInTheDocument();
    expect(working.queryByText("scene-1.svg")).not.toBeInTheDocument();
  });

  it("says when there are no final outputs yet but still lists working files", async () => {
    withArtifacts([STORY_ARTIFACT, ...WORKING_ARTIFACTS]);
    await openRun("run-review");

    expect(
      region("Final outputs").getByText("No videos, thumbnails, captions or metadata yet."),
    ).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Intermediate files" })).toBeInTheDocument();
  });

  it("leaves out the intermediate section when a run has only final outputs", async () => {
    withArtifacts(artifactsFor("en", "episode"));
    await openRun("run-review");

    expect(await region("Final outputs").findByText("English — Episode · 16:9")).toBeVisible();
    expect(screen.queryByRole("region", { name: "Intermediate files" })).not.toBeInTheDocument();
  });

  it("shows an empty state for a run without artifacts", async () => {
    withArtifacts([]);
    await openRun("run-review");

    expect(screen.getByText("No artifacts yet")).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Final outputs" })).not.toBeInTheDocument();
  });
});
