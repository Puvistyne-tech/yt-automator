import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { SchemaForm } from "@/shared/schema-form/SchemaForm";

type Value = Record<string, unknown>;

const STYLES = [
  { const: "paper", title: "Paper cut" },
  { const: "ink", title: "Ink wash" },
];

const schema = {
  type: "object",
  properties: {
    title: { type: "string", title: "Title" },
    names: {
      type: "object",
      title: "Series name",
      properties: {
        en: { type: "string", title: "English" },
        ta: { type: "string", title: "Tamil" },
      },
    },
    music: { type: "boolean", title: "Background music" },
    style: { type: "string", title: "Style", oneOf: STYLES },
    tags: {
      type: "array",
      title: "Tags",
      uniqueItems: true,
      items: { type: "string", enum: ["kindness", "sharing"] },
    },
    cast: {
      type: "array",
      title: "Cast",
      items: { type: "object", title: "Cast member", properties: { name: { type: "string" } } },
    },
  },
};

const uiSchema = {
  "ui:sections": [
    { title: "Story", fields: ["title", "names", "cast"] },
    { title: "Look", fields: ["music", "style", "tags"] },
  ],
  style: { "ui:widget": "cards" },
  tags: { "ui:widget": "checkboxes" },
};

const defaults: Value = {
  title: "Moon",
  names: { en: "Story Time", ta: "Kathai" },
  music: true,
  style: "paper",
  tags: ["kindness"],
  cast: [{ name: "Kavin" }],
};

function Harness({ initial, withDefaults }: { initial: Value; withDefaults: boolean }) {
  const [value, setValue] = useState(initial);
  return (
    <>
      <SchemaForm
        schema={schema}
        uiSchema={uiSchema}
        value={value}
        idPrefix="test"
        onChange={setValue}
        {...(withDefaults ? { defaults } : {})}
      />
      <output data-testid="value">{JSON.stringify(value)}</output>
    </>
  );
}

function setup(changes: Value = {}, withDefaults = true) {
  render(
    <Harness initial={{ ...structuredClone(defaults), ...changes }} withDefaults={withDefaults} />,
  );
  const value = () => JSON.parse(screen.getByTestId("value").textContent ?? "{}") as Value;
  return { user: userEvent.setup(), value };
}

const marker = (label: string) =>
  screen.queryByRole("button", { name: `Reset ${label} to default` });
const sectionReset = (title: string) =>
  screen.queryByRole("button", { name: `Reset ${title} section to defaults` });

describe("SchemaForm defaults", () => {
  it("shows no markers when nothing differs from the defaults", () => {
    setup();

    expect(screen.queryAllByRole("img", { name: "Changed from default" })).toEqual([]);
    expect(sectionReset("Story")).toBeNull();
    expect(sectionReset("Look")).toBeNull();
  });

  it("marks every changed field, per-language values, arrays and cards", () => {
    setup({
      title: "Sun",
      names: { en: "Story Time", ta: "Iravu" },
      music: false,
      style: "ink",
      tags: [],
      cast: [],
    });

    for (const label of ["Title", "Tamil", "Background music", "Style", "Tags", "Cast"]) {
      expect(marker(label)).toBeInTheDocument();
    }
    expect(marker("English")).toBeNull();
    expect(screen.getAllByRole("img", { name: "Changed from default" })).toHaveLength(6);
    expect(marker("Title")).toHaveAttribute("title", "Default: Moon");
  });

  it("marks a field as soon as it is edited and resets it from the keyboard", async () => {
    const { user, value } = setup();
    await user.clear(screen.getByLabelText("Title"));
    await user.type(screen.getByLabelText("Title"), "Sun");
    expect(marker("Title")).toBeInTheDocument();

    marker("Title")?.focus();
    await user.keyboard("{Enter}");

    expect(value().title).toBe("Moon");
    expect(marker("Title")).toBeNull();
    expect(screen.getByLabelText("Title")).toHaveFocus();
  });

  it("resets a changed cards choice and a changed list", async () => {
    const { user, value } = setup({ style: "ink", cast: [] });

    await user.click(marker("Style") as HTMLElement);
    await user.click(marker("Cast") as HTMLElement);

    expect(value()).toMatchObject({ style: "paper", cast: [{ name: "Kavin" }] });
    expect(screen.getByRole("radio", { name: /Paper cut/ })).toBeChecked();
  });

  it("counts changes per section and resets only that section", async () => {
    const { user, value } = setup({
      title: "Sun",
      names: { en: "Bedtime", ta: "Iravu" },
      music: false,
    });
    const story = screen.getByRole("region", { name: "Story" });
    expect(within(story).getByText("3 changed")).toBeInTheDocument();
    expect(
      within(screen.getByRole("region", { name: "Look" })).getByText("1 changed"),
    ).toBeVisible();

    await user.click(sectionReset("Story") as HTMLElement);

    expect(value()).toMatchObject({ title: "Moon", names: defaults.names, music: false });
    expect(sectionReset("Story")).toBeNull();
    expect(within(story).getByRole("heading", { name: "Story" })).toHaveFocus();
    expect(sectionReset("Look")).toBeInTheDocument();
  });

  it("lowers the section count when one field is reset", async () => {
    const { user } = setup({ title: "Sun", names: { en: "Bedtime", ta: "Kathai" } });
    const story = within(screen.getByRole("region", { name: "Story" }));
    expect(story.getByText("2 changed")).toBeInTheDocument();

    await user.click(marker("Title") as HTMLElement);

    expect(story.getByText("1 changed")).toBeInTheDocument();
    expect(marker("English")).toBeInTheDocument();
  });

  it("tracks nothing without defaults", () => {
    setup({ title: "Sun" }, false);

    expect(marker("Title")).toBeNull();
    expect(sectionReset("Story")).toBeNull();
  });
});
