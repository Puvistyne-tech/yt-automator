export function choices(titles: Record<string, string>) {
  return Object.entries(titles).map(([value, title]) => ({ const: value, title }));
}

function colour(title: string, value: string) {
  return { type: "string", format: "color", title, default: value };
}

export const SUBTITLES_SCHEMA = {
  type: "object",
  title: "Subtitles",
  properties: {
    burn_in_episode: { type: "boolean", title: "Burn into the episode", default: false },
    font_size_share: {
      type: "number",
      title: "Font size",
      minimum: 0.01,
      maximum: 0.2,
      default: 0.05,
    },
    bold: { type: "boolean", title: "Bold", default: false },
    primary_color: colour("Text colour", "#FFFFFF"),
    box_background: { type: "boolean", title: "Box behind the text", default: false },
    box_color: colour("Box colour", "#000000"),
    box_opacity: { type: "number", title: "Box opacity", minimum: 0, maximum: 1, default: 0.6 },
    karaoke: { type: "boolean", title: "Karaoke highlight", default: false },
    highlight_color: colour("Highlight colour", "#FFD54A"),
    position: {
      type: "string",
      title: "Position",
      oneOf: choices({ bottom: "Bottom", middle: "Middle", top: "Top" }),
      default: "bottom",
    },
  },
};

export const EPISODE_SCHEMA = {
  type: "object",
  title: "Episode",
  properties: {
    transition: {
      type: "string",
      title: "Transition",
      oneOf: choices({
        cut: "Cut",
        crossfade: "Crossfade",
        fade_through_black: "Fade through black",
      }),
      default: "cut",
    },
    transition_seconds: {
      type: "number",
      title: "Transition length",
      exclusiveMinimum: 0,
      maximum: 3,
      default: 0.5,
    },
    video_quality: {
      type: "string",
      title: "Video quality",
      oneOf: choices({ draft: "Draft", standard: "Standard", high: "High", best: "Best" }),
      default: "standard",
    },
  },
};

export const VIDEO_LOOK_UI = {
  subtitles: {
    primary_color: { "ui:widget": "color" },
    box_color: { "ui:widget": "color" },
    highlight_color: { "ui:widget": "color" },
    box_opacity: { "ui:widget": "range", "ui:options": { step: 0.05 } },
    position: { "ui:widget": "radio" },
  },
  episode: {
    transition: { "ui:widget": "radio" },
    video_quality: { "ui:widget": "select" },
  },
};
