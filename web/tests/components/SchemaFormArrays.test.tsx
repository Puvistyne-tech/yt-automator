import { render, screen, within } from "@testing-library/react";
import { SchemaForm } from "@/shared/schema-form/SchemaForm";

const schema = {
  type: "object",
  properties: {
    topics: { type: "array", title: "Topics", items: { type: "string" } },
    cast: {
      type: "array",
      title: "Cast",
      items: { type: "object", title: "Cast member", properties: { name: { type: "string" } } },
    },
  },
};

const value = { topics: ["planets", "stars"], cast: [{ name: "Kavin" }] };
const ITEM_CONTROLS = /^(Move up|Move down|Duplicate|Remove|Add .*)$/;

function renderArrays(disabled: boolean) {
  render(
    <SchemaForm
      idPrefix="arrays"
      schema={schema}
      value={value}
      onChange={() => undefined}
      disabled={disabled}
    />,
  );
}

describe("SchemaForm arrays", () => {
  it.each([true, false])("names plain items by position when disabled is %s", (disabled) => {
    renderArrays(disabled);

    const topics = within(screen.getByRole("group", { name: "Topics" }));
    expect(topics.getByRole("textbox", { name: "Topics 1" })).toHaveValue("planets");
    expect(topics.getByRole("textbox", { name: "Topics 2" })).toHaveValue("stars");
    expect(screen.queryByText(/^(Topics|Cast)-\d/)).not.toBeInTheDocument();
  });

  it.each([
    ["Move up", 2],
    ["Move down", 2],
    ["Remove", 2],
    ["Add item", 1],
  ])("offers %s on topics while editable", (name, count) => {
    renderArrays(false);
    const topics = within(screen.getByRole("group", { name: "Topics" }));
    expect(topics.getAllByRole("button", { name })).toHaveLength(count);
  });

  it("names the add button after a titled item", () => {
    renderArrays(false);
    const cast = within(screen.getByRole("group", { name: "Cast" }));
    expect(cast.getByRole("button", { name: "Add cast member" })).toBeEnabled();
  });

  it("shows no item controls when read-only", () => {
    renderArrays(true);

    expect(screen.queryAllByRole("button", { name: ITEM_CONTROLS })).toEqual([]);
    expect(screen.getByRole("textbox", { name: "Topics 1" })).toBeDisabled();
  });
});
