import packagedBuiltins from "@/api/mocks/fixtures/builtinTemplates.json";
import { hoursAgo } from "@/api/mocks/fixtures/factories";
import { kidsStoryPipeline } from "@/api/mocks/fixtures/pipeline";
import { narratedEngine } from "@/api/mocks/fixtures/templateEngine";
import type { JsonObject, PipelineTemplate, TemplateAudience } from "@/api/types";

export const USER_TYPE_PREFIX = "t_";

export function makeTemplate(overrides: Partial<PipelineTemplate> = {}): PipelineTemplate {
  const id = overrides.id ?? "space-facts";
  return {
    id,
    type_id: `${USER_TYPE_PREFIX}${id}`,
    engine: narratedEngine.engine_id,
    name: "Space facts",
    description: "Quick, curious facts about planets, stars and space missions.",
    audience: "general",
    status: "ready",
    origin: "blank",
    revision: 3,
    definition: {
      brief: "Five surprising facts about one thing in space, explained simply.",
      tone: "Curious and clear",
      topics: ["planets", "stars", "space missions"],
      category: "27",
      tags: { en: ["space", "science"] },
      hashtags: { en: ["#space"] },
    },
    created_at: hoursAgo(24 * 10),
    updated_at: hoursAgo(24 * 3),
    ...overrides,
  };
}

const BUILTIN_RELEASED_AT = "2026-01-01T00:00:00Z";

interface BuiltinEntry {
  id: string;
  name: string;
  description: string;
  audience: string;
  definition: JsonObject;
}

function builtinTemplate(entry: BuiltinEntry): PipelineTemplate {
  const audience: TemplateAudience = entry.audience === "kids" ? "kids" : "general";
  return makeTemplate({
    ...entry,
    type_id: entry.id,
    audience,
    origin: "builtin",
    revision: 1,
    created_at: BUILTIN_RELEASED_AT,
    updated_at: BUILTIN_RELEASED_AT,
  });
}

export const BUILTIN_TEMPLATES: PipelineTemplate[] = [
  builtinTemplate({
    id: kidsStoryPipeline.type_id,
    name: kidsStoryPipeline.name,
    description: kidsStoryPipeline.description,
    audience: "kids",
    definition: {},
  }),
  ...packagedBuiltins.map(builtinTemplate),
];

export const USER_TEMPLATES: PipelineTemplate[] = [
  makeTemplate(),
  makeTemplate({
    id: "history-five",
    name: "Ancient empires",
    description: "One ancient empire told from its rise to its fall.",
    status: "draft",
    revision: 1,
    definition: {
      brief: "One event from history, what led to it and why it still matters.",
      length: "long",
      tone: "Serious and vivid",
    },
    created_at: hoursAgo(24 * 2),
    updated_at: hoursAgo(24 * 2),
  }),
];
