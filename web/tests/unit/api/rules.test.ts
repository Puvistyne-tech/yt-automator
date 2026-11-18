import { isKidsPipeline } from "@/api/capabilities";
import { kidsStoryPipeline } from "@/api/mocks/fixtures/pipeline";
import { runPath } from "@/api/paths";
import { canCancel, canDelete, canRetry } from "@/api/runRules";
import type { RunStatus } from "@/api/types";

describe("isKidsPipeline", () => {
  it("detects kids pipelines by capability", () => {
    expect(isKidsPipeline(kidsStoryPipeline)).toBe(true);
    expect(isKidsPipeline({ ...kidsStoryPipeline, capabilities: [] })).toBe(false);
    expect(isKidsPipeline(undefined)).toBe(false);
  });
});

describe("run rules", () => {
  it.each<[RunStatus, boolean, boolean, boolean]>([
    ["queued", true, false, false],
    ["running", true, false, false],
    ["awaiting_review", true, true, true],
    ["approved", true, true, true],
    ["rejected", false, true, true],
    ["publishing", false, false, false],
    ["published", false, false, true],
    ["failed", false, true, true],
    ["cancelled", false, true, true],
  ])("a %s run: cancel %s, retry %s, delete %s, as the backend allows", (status, ...allowed) => {
    expect([canCancel(status), canRetry(status), canDelete(status)]).toEqual(allowed);
  });
});

describe("runPath", () => {
  it("links to the run detail route with an encoded id", () => {
    expect(runPath({ id: "run-1" })).toBe("/runs/run-1");
    expect(runPath({ id: "a/b c" })).toBe("/runs/a%2Fb%20c");
  });
});
