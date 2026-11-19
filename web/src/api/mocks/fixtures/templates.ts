import { hoursAgo } from "@/api/mocks/fixtures/factories";
import { kidsStoryPipeline } from "@/api/mocks/fixtures/pipeline";
import { narratedEngine } from "@/api/mocks/fixtures/templateEngine";
import type { PipelineTemplate } from "@/api/types";

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
      ...narratedEngine.blank.general,
      structure: "list",
      brief: "Five surprising facts about one thing in space, explained simply.",
      topics: ["planets", "stars", "space missions"],
      tags: ["space", "science"],
      hashtags: ["#space"],
    },
    created_at: hoursAgo(24 * 10),
    updated_at: hoursAgo(24 * 3),
    ...overrides,
  };
}

export const BUILTIN_TEMPLATES: PipelineTemplate[] = [
  makeTemplate({
    id: kidsStoryPipeline.type_id,
    type_id: kidsStoryPipeline.type_id,
    name: kidsStoryPipeline.name,
    description: kidsStoryPipeline.description,
    audience: "kids",
    origin: "builtin",
    revision: 1,
    definition: {
      ...narratedEngine.blank.kids,
      brief: "Gentle bedtime adventures with a clear moral.",
      topics: ["kindness", "sharing", "courage"],
    },
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  }),
];

export const USER_TEMPLATES: PipelineTemplate[] = [
  makeTemplate(),
  makeTemplate({
    id: "history-five",
    name: "History in five minutes",
    description: "One historical event told from start to finish.",
    status: "draft",
    revision: 1,
    definition: {
      ...narratedEngine.blank.general,
      brief: "One event from history, what led to it and why it still matters.",
      length: "standard",
      tone: "serious",
    },
    created_at: hoursAgo(24 * 2),
    updated_at: hoursAgo(24 * 2),
  }),
];
