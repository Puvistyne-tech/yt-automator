import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SchemaForm } from "@/shared/schema-form/SchemaForm";
import { widgets } from "@/shared/schema-form/widgets";

const SPEC = resolve(process.cwd(), "..", "docs", "spec", "platform.md");
const WIDGET_LINE = "- `ui:widget`: one of ";

function specWidgets(): string[] {
  const line = readFileSync(SPEC, "utf-8")
    .split("\n")
    .find((text) => text.includes(WIDGET_LINE));
  const listed = (line ?? "").split(WIDGET_LINE)[1]?.split("(")[0] ?? "";
  return [...listed.matchAll(/`([a-z]+)`/g)].map((match) => match[1] ?? "").sort();
}

function registryName(widget: string): string {
  return `${widget.charAt(0).toUpperCase()}${widget.slice(1)}Widget`;
}

const choice = { type: "string", enum: ["calm", "funny"] };
const schema = {
  type: "object",
  properties: {
    textarea: { type: "string", title: "Textarea field" },
    select: { ...choice, title: "Select field" },
    radio: { ...choice, title: "Radio field", default: "calm" },
    checkboxes: { type: "array", title: "Checkboxes field", uniqueItems: true, items: choice },
    range: { type: "number", title: "Range field", minimum: 0, maximum: 1, multipleOf: 0.1 },
    color: { type: "string", title: "Color field" },
  },
};

function uiSchemaFor(names: string[], step?: unknown) {
  const hints = Object.fromEntries(names.map((name) => [name, { "ui:widget": name }]));
  return { ...hints, range: { "ui:widget": "range", "ui:options": { step } } };
}

function renderWidgets(step?: unknown, onChange = vi.fn()) {
  render(
    <SchemaForm
      schema={schema}
      uiSchema={uiSchemaFor(specWidgets(), step)}
      value={{ radio: "calm", range: 0.5 }}
      idPrefix="widgets"
      onChange={onChange}
    />,
  );
  return onChange;
}

describe("contract widgets", () => {
  it("reads the widget list from the spec and registers a widget for each name", () => {
    const names = specWidgets();
    expect(names).toEqual(["checkboxes", "color", "radio", "range", "select", "textarea"]);
    expect(names.filter((name) => !(registryName(name) in widgets))).toEqual([]);
  });

  it("renders every contract widget name as its own control", () => {
    renderWidgets();

    expect(screen.getByRole("textbox", { name: "Textarea field" }).tagName).toBe("TEXTAREA");
    expect(screen.getByRole("combobox", { name: "Select field" })).toBeInTheDocument();
    expect(screen.getByRole("group", { name: "Radio field" })).toHaveClass("radio-options");
    expect(screen.getByRole("radio", { name: "calm" })).toBeChecked();
    expect(screen.getAllByRole("checkbox", { name: "calm" })).toHaveLength(1);
    expect(screen.getByRole("slider", { name: "Range field" })).toHaveAttribute("step", "0.1");
    expect(screen.getByLabelText("Color field")).toHaveAttribute("type", "color");
  });

  it("stores the picked radio option", async () => {
    const onChange = renderWidgets();

    await userEvent.setup().click(screen.getByRole("radio", { name: "funny" }));

    expect(onChange).toHaveBeenLastCalledWith(expect.objectContaining({ radio: "funny" }));
  });

  it.each([
    [0.25, "0.25"],
    [0, "0.1"],
    [-1, "0.1"],
    [Number.POSITIVE_INFINITY, "0.1"],
    ["0.5", "0.1"],
    [undefined, "0.1"],
  ])("uses step %s when valid and the schema step otherwise", (step, expected) => {
    renderWidgets(step);

    expect(screen.getByRole("slider", { name: "Range field" })).toHaveAttribute("step", expected);
  });
});
