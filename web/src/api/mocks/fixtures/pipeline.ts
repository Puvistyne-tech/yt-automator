import { KIDS_CAPABILITY } from "@/api/capabilities";
import { STYLE_CHOICES } from "@/api/mocks/fixtures/styleChoices";
import {
  choices,
  EPISODE_SCHEMA,
  SUBTITLES_SCHEMA,
  VIDEO_LOOK_UI,
} from "@/api/mocks/fixtures/videoLook";
import type { JsonObject, PipelineDescriptor } from "@/api/types";

const castMember = {
  type: "object",
  title: "Cast member",
  required: ["name", "role"],
  properties: {
    name: { type: "string", title: "Name", minLength: 1 },
    role: {
      type: "string",
      title: "Role",
      oneOf: choices({ hero: "Hero", friend: "Friend", mentor: "Mentor", trickster: "Trickster" }),
      default: "friend",
    },
    description: {
      type: "string",
      title: "Look and personality",
      description: "Used to keep the character consistent across scenes.",
      default: "",
    },
    color: { type: "string", title: "Signature colour", default: "#f59e0b" },
  },
};

const settingsSchema = {
  type: "object",
  title: "Kids story videos settings",
  required: ["series_name", "cast", "story_length_minutes"],
  properties: {
    series_name: {
      type: "string",
      title: "Series name",
      description: "Appears in every title and on the intro card.",
      minLength: 1,
      maxLength: 60,
      default: "Story Time",
    },
    premise: {
      type: "string",
      title: "Series premise",
      description: "One paragraph the story writer follows for every episode.",
      default: "Gentle bedtime adventures in a village by the sea.",
    },
    story_length_minutes: {
      type: "integer",
      title: "Story length (minutes)",
      minimum: 2,
      maximum: 12,
      default: 5,
    },
    moral_themes: {
      type: "array",
      title: "Moral themes",
      description: "Each episode picks one theme from this list.",
      uniqueItems: true,
      minItems: 1,
      items: {
        type: "string",
        enum: ["kindness", "honesty", "sharing", "courage", "patience", "gratitude"],
      },
      default: ["kindness", "sharing"],
    },
    cast: {
      type: "array",
      title: "Cast",
      description: "Recurring characters. The first hero leads every story.",
      minItems: 1,
      items: castMember,
      default: [
        { name: "Kavin", role: "hero", description: "A curious elephant calf", color: "#f59e0b" },
        { name: "Mynah", role: "friend", description: "A chatty bird", color: "#10b981" },
      ],
    },
    look: {
      type: "object",
      title: "Visual style",
      description: "The look of every picture.",
      properties: {
        visual_style: {
          type: "string",
          title: "Style",
          oneOf: STYLE_CHOICES,
          default: "watercolour_storybook",
        },
      },
    },
    voices: {
      type: "object",
      title: "Narration voices",
      description: "Voice used for each language.",
      properties: {
        en: { type: "string", title: "English voice", default: "warm_storyteller" },
        ta: { type: "string", title: "Tamil voice", default: "paati_kathai" },
      },
    },
    music: {
      type: "object",
      title: "Background music",
      properties: {
        enabled: { type: "boolean", title: "Play background music", default: true },
        volume: {
          type: "number",
          title: "Music volume",
          minimum: 0,
          maximum: 1,
          multipleOf: 0.05,
          default: 0.3,
        },
      },
    },
    subtitles: SUBTITLES_SCHEMA,
    episode: EPISODE_SCHEMA,
  },
};

const uiSchema = {
  "ui:sections": [
    { title: "Story", fields: ["series_name", "premise", "story_length_minutes", "moral_themes"] },
    { title: "Characters", fields: ["cast"] },
    { title: "Visual style", fields: ["look"] },
    { title: "Sound", fields: ["voices", "music"] },
    { title: "Subtitles", fields: ["subtitles"] },
    { title: "Videos", fields: ["episode"] },
  ],
  "ui:basic": [
    "series_name",
    "story_length_minutes",
    "look.visual_style",
    "voices",
    "music.enabled",
    "subtitles.burn_in_episode",
  ],
  premise: { "ui:widget": "textarea", "ui:options": { rows: 3 } },
  look: { visual_style: { "ui:widget": "cards" } },
  story_length_minutes: { "ui:widget": "range" },
  moral_themes: { "ui:widget": "checkboxes" },
  cast: {
    items: {
      "ui:order": ["name", "role", "description", "color"],
      description: { "ui:widget": "textarea", "ui:options": { rows: 2 } },
      color: { "ui:widget": "color" },
    },
  },
  music: { volume: { "ui:widget": "range", "ui:options": { step: 0.05 } } },
  ...VIDEO_LOOK_UI,
};

function defaultsOf(schema: JsonObject): JsonObject {
  const properties = (schema.properties ?? {}) as Record<string, JsonObject>;
  return Object.fromEntries(
    Object.entries(properties).map(([key, property]) => [
      key,
      "default" in property ? property.default : defaultsOf(property),
    ]),
  );
}

export const kidsStoryPipeline: PipelineDescriptor = {
  type_id: "kids_story",
  name: "Kids story videos",
  description:
    "Illustrated moral stories for young children, narrated in several languages, with a long episode and a vertical short cut from the same story.",
  version: "1.0.0",
  settings_schema: settingsSchema,
  default_settings: defaultsOf(settingsSchema),
  ui_schema: uiSchema,
  stages: [
    { id: "story", title: "Write story", description: "Drafts the story and scene list." },
    { id: "images", title: "Illustrate scenes", description: "Generates one image per scene." },
    { id: "motion", title: "Animate", description: "Adds gentle motion to each image." },
    { id: "voice", title: "Narrate", description: "Synthesises narration per language." },
    { id: "music", title: "Score music", description: "Adds background music." },
    { id: "render", title: "Render", description: "Assembles videos, subtitles and thumbnails." },
  ],
  languages: [
    { code: "en", name: "English" },
    { code: "ta", name: "Tamil" },
  ],
  variants: [
    { id: "episode", name: "Episode", aspect: "16:9", description: "Full story, landscape." },
    { id: "short", name: "Short", aspect: "9:16", description: "Under 60 seconds, vertical." },
  ],
  capabilities: [KIDS_CAPABILITY],
};
