import { kidsStoryPipeline } from "@/api/mocks/fixtures/pipeline";
import { BUILTIN_TEMPLATES, makeTemplate } from "@/api/mocks/fixtures/templates";
import type { LanguageOption, PipelineDescriptor } from "@/api/types";
import { draftFromTemplate } from "@/features/pipeline-templates/model/form";
import {
  chosenLanguage,
  engineLanguages,
  numberedScenes,
  previewRequest,
} from "@/features/pipeline-templates/model/preview";

const ENGLISH = { code: "en", name: "English" };
const TAMIL = { code: "ta", name: "Tamil" };
const HINDI = { code: "hi", name: "Hindi" };

function served(typeId: string, languages: LanguageOption[]): PipelineDescriptor {
  return { ...kidsStoryPipeline, type_id: typeId, languages };
}

describe("engineLanguages", () => {
  const templates = [...BUILTIN_TEMPLATES, makeTemplate(), makeTemplate({ engine: "other" })];

  it("joins the languages of the pipelines the engine's templates serve, once each", () => {
    const pipelines = [
      served("kids_story", [ENGLISH, TAMIL]),
      served("t_space-facts", [TAMIL, HINDI]),
      served("static", [{ code: "fr", name: "French" }]),
    ];
    expect(engineLanguages("narrated_video", templates, pipelines)).toEqual([
      ENGLISH,
      TAMIL,
      HINDI,
    ]);
  });

  it("offers nothing while nothing is served", () => {
    expect(engineLanguages("narrated_video", templates, [])).toEqual([]);
  });
});

describe("chosenLanguage", () => {
  it.each([
    ["ta", [ENGLISH, TAMIL], "ta"],
    ["", [ENGLISH, TAMIL], "en"],
    ["", [], null],
  ])("sends %j from %j as %j", (choice, languages, expected) => {
    expect(chosenLanguage(choice, languages)).toBe(expected);
  });
});

describe("numberedScenes", () => {
  it("numbers scenes from one in their order", () => {
    const scenes = ["first", "second", "third"].map((narration) => ({
      narration,
      heading: "",
      action: "",
    }));
    expect(numberedScenes(scenes).map((entry) => [entry.number, entry.scene.narration])).toEqual([
      [1, "first"],
      [2, "second"],
      [3, "third"],
    ]);
  });
});

describe("previewRequest", () => {
  it("sends the unsaved draft with its status, the language and the topic", () => {
    const draft = { ...draftFromTemplate(makeTemplate()), name: "  Sky  " };
    expect(previewRequest(draft, "narrated_video", { language: "ta", topic: "tides" })).toEqual({
      engine: "narrated_video",
      name: "Sky",
      description: draft.description,
      audience: "general",
      status: "ready",
      definition: draft.definition,
      language: "ta",
      topic: "tides",
    });
  });
});
