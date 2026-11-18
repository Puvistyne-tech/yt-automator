import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SchemaForm } from "@/shared/schema-form/SchemaForm";

function entry(value: string, group: string, swatches?: unknown[]) {
  return {
    const: value,
    title: `${value} look`,
    description: `A ${value} kind of picture.`,
    "x-group": group,
    ...(swatches ? { "x-swatches": swatches } : {}),
  };
}

const MANY = [
  entry("sunny", "Painted", ["#FF0000", "#00FF00", "red"]),
  entry("misty", "Painted"),
  entry("blocky", "Graphic", ["#0000FF"]),
  entry("inky", "Drawn"),
  entry("chalky", "Drawn"),
  entry("glossy", "Graphic"),
  entry("woolly", "Crafted"),
  entry("papery", "Crafted"),
  { const: "own", title: "Your own", description: "Write it yourself." },
];

function renderCards(oneOf: unknown[] = MANY, disabled = false, onChange = vi.fn()) {
  const schema = {
    type: "object",
    properties: { look: { type: "string", title: "Look", oneOf, default: "sunny" } },
  };
  render(
    <SchemaForm
      schema={schema}
      uiSchema={{ look: { "ui:widget": "cards" } }}
      value={{ look: "sunny" }}
      idPrefix="cards"
      onChange={onChange}
      disabled={disabled}
    />,
  );
  return onChange;
}

function titles(): string[] {
  return screen.getAllByRole("radio").map((radio) => radio.closest("label")?.textContent ?? "");
}

describe("cards widget", () => {
  it("renders every option as a card in a labelled radio group with the current one checked", () => {
    renderCards();

    const group = screen.getByRole("radiogroup", { name: "Look" });
    expect(within(group).getAllByRole("radio")).toHaveLength(MANY.length);
    expect(screen.getByRole("radio", { name: /sunny look/ })).toBeChecked();
    expect(screen.getByText("A misty kind of picture.")).toBeInTheDocument();
    expect(screen.getByText("Selected: sunny look")).toBeInTheDocument();
  });

  it("stores the clicked card", async () => {
    const onChange = renderCards();

    await userEvent.setup().click(screen.getByText("inky look"));

    expect(onChange).toHaveBeenLastCalledWith(expect.objectContaining({ look: "inky" }));
  });

  it("moves the selection with the arrow keys", async () => {
    const onChange = renderCards();
    const user = userEvent.setup();

    screen.getByRole("radio", { name: /sunny look/ }).focus();
    await user.keyboard("{ArrowDown}");

    expect(onChange).toHaveBeenLastCalledWith(expect.objectContaining({ look: "misty" }));
  });

  it("groups cards under their labels in order of first appearance", () => {
    renderCards();

    const headings = screen
      .getAllByText(/^(Painted|Graphic|Drawn|Crafted)$/, { selector: "p" })
      .map((node) => node.textContent);
    expect(headings).toEqual(["Painted", "Graphic", "Drawn", "Crafted"]);
    expect(
      titles()
        .slice(0, 4)
        .map((text) => text.split(" look")[0]),
    ).toEqual(["sunny", "misty", "blocky", "glossy"]);
  });

  it("filters by group and by search text", async () => {
    renderCards();
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: "Drawn" }));
    expect(screen.getAllByRole("radio")).toHaveLength(2);
    expect(screen.getByRole("button", { name: "Drawn" })).toHaveAttribute("aria-pressed", "true");

    await user.click(screen.getByRole("button", { name: "All" }));
    await user.type(screen.getByRole("searchbox", { name: "Search Look" }), "kind wool");
    expect(titles()).toEqual(["woolly lookA woolly kind of picture."]);

    await user.clear(screen.getByRole("searchbox", { name: "Search Look" }));
    await user.type(screen.getByRole("searchbox", { name: "Search Look" }), "nothing like it");
    expect(screen.queryAllByRole("radio")).toHaveLength(0);
    expect(screen.getByText("Nothing matches. Clear the search.")).toBeInTheDocument();
  });

  it("draws only valid colour swatches", () => {
    renderCards();

    const sunny = screen.getByRole("radio", { name: /sunny look/ }).closest("label");
    const swatches = sunny?.querySelectorAll(".choice-card-swatch") ?? [];
    expect([...swatches].map((node) => (node as HTMLElement).style.background)).toEqual([
      "rgb(255, 0, 0)",
      "rgb(0, 255, 0)",
    ]);
    const misty = screen.getByRole("radio", { name: /misty/ }).closest("label");
    expect(misty?.querySelector(".choice-card-swatches")).toBeNull();
  });

  it("offers no search or chips for a short list without groups", () => {
    renderCards([
      { const: "a", title: "A" },
      { const: "b", title: "B" },
    ]);

    expect(screen.queryByRole("searchbox")).toBeNull();
    expect(screen.queryByRole("button")).toBeNull();
    expect(screen.getAllByRole("radio")).toHaveLength(2);
  });

  it("locks every card when the form is disabled", () => {
    renderCards(MANY, true);

    expect(
      screen.getAllByRole("radio").every((radio) => (radio as HTMLInputElement).disabled),
    ).toBe(true);
  });
});
