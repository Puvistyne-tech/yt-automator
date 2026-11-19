import { STYLE_CHOICES } from "@/api/mocks/fixtures/styleChoices";
import { choices } from "@/api/mocks/fixtures/videoLook";
import type { EngineSummary, JsonObject } from "@/api/types";

const words = (title: string, description: string) => ({
  type: "array",
  title,
  description,
  items: { type: "string" },
});

const text = (title: string, description: string) => ({ type: "string", title, description });

const definitionSchema: JsonObject = {
  type: "object",
  title: "Pipeline definition",
  properties: {
    structure: {
      type: "string",
      title: "Structure",
      description: "How every video is put together.",
      oneOf: choices({
        story: "Story with characters",
        explainer: "Explainer",
        list: "List of facts",
        countdown: "Countdown",
        quiz: "Quiz",
      }),
    },
    brief: text(
      "Brief",
      "What the videos are about, in a few sentences. The script writer follows it.",
    ),
    length: {
      type: "string",
      title: "Length",
      oneOf: choices({
        short: "Short (about 2 minutes)",
        standard: "Standard (about 5 minutes)",
        long: "Long (about 10 minutes)",
      }),
    },
    tone: {
      type: "string",
      title: "Tone",
      oneOf: choices({ calm: "Calm", curious: "Curious", upbeat: "Upbeat", serious: "Serious" }),
    },
    topics: words("Topics", "Each video picks one topic from this list."),
    visual_style: { type: "string", title: "Visual style", oneOf: STYLE_CHOICES },
    music_mood: {
      type: "string",
      title: "Music mood",
      oneOf: choices({
        gentle: "Gentle",
        uplifting: "Uplifting",
        dramatic: "Dramatic",
        none: "No music",
      }),
    },
    title_template: text("Title", "Placeholders: {title}, {series}."),
    description_template: text("Description", "Placeholders: {title}, {summary}."),
    tags: words("Tags", "Added to every upload."),
    hashtags: words("Hashtags", "Added to the end of every description."),
  },
};

const definitionUiSchema: JsonObject = {
  "ui:sections": [
    { title: "What it makes", fields: ["structure", "brief", "length", "tone", "topics"] },
    { title: "Look and sound", fields: ["visual_style", "music_mood"] },
    { title: "Publishing", fields: ["title_template", "description_template", "tags", "hashtags"] },
  ],
  brief: { "ui:widget": "textarea", "ui:options": { rows: 3 } },
  description_template: { "ui:widget": "textarea", "ui:options": { rows: 3 } },
  visual_style: { "ui:widget": "cards" },
};

const KIDS_BLANK: JsonObject = {
  structure: "story",
  brief: "",
  length: "standard",
  tone: "calm",
  topics: [],
  visual_style: "watercolour_storybook",
  music_mood: "gentle",
  title_template: "{title} | {series}",
  description_template: "{summary}\n\nA gentle story for young children.",
  tags: ["kids stories"],
  hashtags: ["#kidsstories"],
};

const GENERAL_BLANK: JsonObject = {
  ...KIDS_BLANK,
  structure: "explainer",
  tone: "curious",
  visual_style: "animated_3d",
  music_mood: "uplifting",
  title_template: "{title}",
  description_template: "{summary}",
  tags: [],
  hashtags: [],
};

export const narratedEngine: EngineSummary = {
  engine_id: "narrated_video",
  name: "Narrated video",
  definition_schema: definitionSchema,
  definition_ui_schema: definitionUiSchema,
  blank: { kids: KIDS_BLANK, general: GENERAL_BLANK },
};
