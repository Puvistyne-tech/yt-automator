import { makeArtifact, makeRun } from "@/api/mocks/fixtures/factories";
import { kidsStoryPipeline } from "@/api/mocks/fixtures/pipeline";
import type { ArtifactKind } from "@/api/types";
import {
  finalOutputs,
  groupArtifacts,
  intermediateByStage,
  isFinalOutput,
  isTallArtifact,
  posterFor,
  splitGroup,
} from "@/features/run-detail/artifacts";
import { itemAt } from "../../helpers/itemAt";

describe("groupArtifacts", () => {
  it("groups by language and variant in run and pipeline order, shared first", () => {
    const run = makeRun({
      languages: ["ta", "en"],
      artifacts: [
        makeArtifact({ id: "a1", language: "en", variant: "short" }),
        makeArtifact({ id: "a2", language: "ta", variant: "episode" }),
        makeArtifact({ id: "a3", language: null, variant: null, kind: "text" }),
        makeArtifact({ id: "a4", language: "en", variant: "episode" }),
        makeArtifact({ id: "a5", language: "en", variant: "episode", kind: "thumbnail" }),
        makeArtifact({ id: "a6", language: "en", variant: null }),
      ],
    });
    const groups = groupArtifacts(run, kidsStoryPipeline);
    expect(groups.map((g) => g.title)).toEqual([
      "Shared across languages",
      "Tamil — Episode · 16:9",
      "English — All outputs",
      "English — Episode · 16:9",
      "English — Short · 9:16",
    ]);
    expect(groups[3]?.artifacts.map((a) => a.id)).toEqual(["a4", "a5"]);
    expect(posterFor(itemAt(groups, 3))?.id).toBe("a5");
    expect(posterFor(itemAt(groups, 1))).toBeUndefined();
  });

  it("names all-language groups and unknown variants, ordering unknowns last", () => {
    const run = makeRun({
      languages: ["en"],
      artifacts: [
        makeArtifact({ id: "b1", language: "fr", variant: "reel" }),
        makeArtifact({ id: "b2", language: "en", variant: "reel" }),
        makeArtifact({ id: "b3", language: null, variant: "episode" }),
      ],
    });
    expect(groupArtifacts(run, kidsStoryPipeline).map((g) => g.title)).toEqual([
      "All languages — Episode · 16:9",
      "English — reel",
      "fr — reel",
    ]);
  });

  it("falls back to raw codes without a pipeline", () => {
    const run = makeRun({ artifacts: [makeArtifact({ language: "fr", variant: "reel" })] });
    expect(groupArtifacts(run)[0]?.title).toBe("fr — reel");
  });

  it("splits a group into media, documents, captions and poster", () => {
    const run = makeRun({
      artifacts: [
        makeArtifact({ id: "v" }),
        makeArtifact({ id: "t", kind: "thumbnail" }),
        makeArtifact({ id: "s", kind: "subtitle" }),
        makeArtifact({ id: "m", kind: "metadata" }),
      ],
    });
    const parts = splitGroup(itemAt(groupArtifacts(run, kidsStoryPipeline), 0));
    expect(parts.media.map((a) => a.id)).toEqual(["v", "t"]);
    expect(parts.documents.map((a) => a.id)).toEqual(["s", "m"]);
    expect(parts.captions?.id).toBe("s");
    expect(parts.poster?.id).toBe("t");
  });

  it("treats per-language videos, thumbnails, captions and metadata as final outputs", () => {
    const final = (kind: ArtifactKind, language: string | null) =>
      isFinalOutput(makeArtifact({ kind, language }));
    expect(
      ["video", "thumbnail", "subtitle", "metadata"].map((k) => final(k as ArtifactKind, "en")),
    ).toEqual([true, true, true, true]);
    expect(final("video", null)).toBe(false);
    expect(final("image", "en")).toBe(false);
    expect(final("audio", "en")).toBe(false);
    expect(final("text", null)).toBe(false);
  });

  it("splits a run into final outputs and intermediate files by stage in run order", () => {
    const run = makeRun({
      artifacts: [
        makeArtifact({ id: "clip", stage_id: "motion", language: null, variant: "episode" }),
        makeArtifact({ id: "final", stage_id: "render", language: "en", variant: "episode" }),
        makeArtifact({ id: "scene", kind: "image", stage_id: "images", language: null }),
        makeArtifact({ id: "odd", kind: "text", stage_id: "extra", language: null }),
        makeArtifact({ id: "story", kind: "text", stage_id: "story", language: null }),
        makeArtifact({ id: "scene2", kind: "image", stage_id: "images", language: null }),
      ],
    });

    expect(finalOutputs(run).map((a) => a.id)).toEqual(["final"]);
    expect(
      intermediateByStage(run).map((s) => [s.stageId, s.title, s.artifacts.map((a) => a.id)]),
    ).toEqual([
      ["story", "Write story", ["story"]],
      ["images", "Illustrate scenes", ["scene", "scene2"]],
      ["motion", "Animate", ["clip"]],
      ["extra", "extra", ["odd"]],
    ]);
  });

  it("decides tall previews from the variant aspect, then the frame size", () => {
    expect(isTallArtifact(makeArtifact({ variant: "short" }), kidsStoryPipeline)).toBe(true);
    expect(isTallArtifact(makeArtifact({ variant: "episode" }), kidsStoryPipeline)).toBe(false);
    const portrait = makeArtifact({ variant: "reel", meta: { width: 1080, height: 1920 } });
    expect(isTallArtifact(portrait, kidsStoryPipeline)).toBe(true);
    expect(isTallArtifact(makeArtifact({ variant: null, meta: {} }))).toBe(false);
  });
});
