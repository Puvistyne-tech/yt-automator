import { render, screen } from "@testing-library/react";
import { SchemaForm } from "@/shared/schema-form/SchemaForm";

const SECTION_TITLES = [
  "Series",
  "Story",
  "Pictures and motion",
  "Sound",
  "Subtitles",
  "Videos",
  "Publishing",
  "Quality checks",
];

const SECTION_FIELDS = [
  ["series", "cast"],
  ["story", "safety"],
  ["visuals"],
  ["voice", "music", "sound_effects"],
  ["subtitles"],
  ["episode", "short"],
  ["thumbnail", "metadata"],
  ["quality"],
];

const text = (title: string) => ({ type: "string", title, default: "" });

const localized = {
  type: "object",
  title: "LocalizedText",
  properties: { en: text("English"), ta: text("Tamil") },
};

const series = {
  type: "object",
  title: "SeriesSettings",
  properties: {
    premise: text("Series premise"),
    tagline: text("Tagline"),
    name: { $ref: "#/$defs/LocalizedText", title: "Series name" },
  },
};

const character = {
  type: "object",
  title: "Character",
  properties: {
    id: text("Character id"),
    palette: { type: "array", title: "Colour palette", items: { type: "string" } },
  },
};

const music = {
  type: "object",
  title: "MusicSettings",
  properties: {
    volume: { type: "number", title: "Music volume", minimum: 0, maximum: 1, default: 0.18 },
  },
};

function section(name: string) {
  return { $ref: `#/$defs/${name}`, title: name };
}

const placeholderSections = SECTION_FIELDS.flat().filter(
  (name) => !["series", "cast", "music"].includes(name),
);

const settingsSchema = {
  type: "object",
  additionalProperties: false,
  properties: {
    series: section("SeriesSettings"),
    cast: { type: "array", title: "Cast", items: { $ref: "#/$defs/Character" } },
    music: section("MusicSettings"),
    ...Object.fromEntries(
      placeholderSections.map((name) => [
        name,
        { type: "object", title: name, properties: { enabled: { type: "boolean" } } },
      ]),
    ),
  },
  $defs: {
    LocalizedText: localized,
    SeriesSettings: series,
    Character: character,
    MusicSettings: music,
  },
};

const pipelineUiSchema = {
  "ui:sections": SECTION_TITLES.map((title, index) => ({
    title,
    fields: SECTION_FIELDS[index],
  })),
  series: {
    "ui:order": ["name", "*"],
    premise: { "ui:widget": "textarea", "ui:options": { rows: 3 } },
  },
  cast: { items: { palette: { items: { "ui:widget": "color" } } } },
  music: { volume: { "ui:widget": "range", "ui:options": { step: 0.01 } } },
};

function follows(first: Element, second: Element): boolean {
  return (first.compareDocumentPosition(second) & Node.DOCUMENT_POSITION_FOLLOWING) !== 0;
}

function renderPipelineForm() {
  render(
    <SchemaForm
      schema={settingsSchema}
      uiSchema={pipelineUiSchema}
      value={{ cast: [{ id: "kavin", palette: ["#8FA3B8"] }] }}
      idPrefix="pipeline"
      onChange={() => undefined}
    />,
  );
}

describe("SchemaForm with the pipeline ui_schema shape", () => {
  it("groups the settings into the pipeline's titled sections in order", () => {
    renderPipelineForm();

    const headings = screen.getAllByRole("heading", { level: 3 }).map((h) => h.textContent);
    expect(headings).toEqual(SECTION_TITLES);
  });

  it("applies the field order and widget hints inside the sections", () => {
    renderPipelineForm();

    const seriesName = screen.getByRole("group", { name: "Series name" });
    const premise = screen.getByRole("textbox", { name: "Series premise" });
    const tagline = screen.getByRole("textbox", { name: "Tagline" });
    expect(follows(seriesName, premise)).toBe(true);
    expect(follows(premise, tagline)).toBe(true);
    expect(premise).toHaveAttribute("rows", "3");
    expect(screen.getByRole("slider", { name: "Music volume" })).toHaveAttribute("step", "0.01");
    expect(screen.getByText("#8FA3B8")).toBeInTheDocument();
  });
});
