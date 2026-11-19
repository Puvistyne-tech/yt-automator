export const filterSchema = {
  type: "object",
  properties: {
    series: { $ref: "#/$defs/Series", title: "Series" },
    tone: {
      type: "string",
      title: "Tone",
      description: "How the story feels.",
      oneOf: [{ const: "calm", title: "Calm" }],
    },
    music: {
      anyOf: [{ $ref: "#/$defs/Music" }, { type: "null" }],
      title: "Music",
    },
    cast: { type: "array", title: "Cast", items: { $ref: "#/$defs/Member" } },
  },
  $defs: {
    Series: {
      type: "object",
      properties: {
        name: { type: "object", title: "Series name", properties: { en: { title: "English" } } },
        tagline: { type: "string", title: "Tagline", description: "A short line for covers." },
      },
    },
    Music: {
      type: "object",
      title: "Music settings",
      properties: {
        enabled: { type: "boolean", title: "Background music" },
        volume: { type: "number", title: "Volume" },
      },
    },
    Member: { type: "object", properties: { name: { type: "string", title: "Name" } } },
  },
};
