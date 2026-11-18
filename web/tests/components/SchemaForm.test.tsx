import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { SchemaForm } from "@/shared/schema-form/SchemaForm";

type Value = Record<string, unknown>;

const schema = {
  type: "object",
  required: ["title"],
  properties: {
    title: { type: "string", title: "Title", description: "Shown on the video." },
    mood: { type: "string", title: "Mood", enum: ["calm", "funny"] },
    minutes: { type: "integer", title: "Minutes", minimum: 1, maximum: 10 },
    music: { type: "boolean", title: "Background music" },
    tags: {
      type: "array",
      title: "Tags",
      uniqueItems: true,
      items: { type: "string", enum: ["kindness", "sharing"] },
    },
    cast: {
      type: "array",
      title: "Cast",
      items: {
        type: "object",
        title: "Cast member",
        properties: { name: { type: "string", title: "Name" } },
      },
    },
  },
};

const uiSchema = {
  "ui:sections": [
    { title: "Story", fields: ["title", "mood", "cast"] },
    { title: "Sound", fields: ["music"] },
  ],
  tags: { "ui:widget": "checkboxes" },
};

function Harness({
  initial,
  errors,
  onValue,
}: {
  initial: Value;
  errors?: Record<string, string>;
  onValue: (value: Value) => void;
}) {
  const [value, setValue] = useState(initial);
  return (
    <SchemaForm
      schema={schema}
      uiSchema={uiSchema}
      value={value}
      idPrefix="test"
      {...(errors === undefined ? {} : { errors })}
      onChange={(next) => {
        setValue(next);
        onValue(next);
      }}
    />
  );
}

function setup(
  initial: Value = { title: "Moon", cast: [{ name: "Kutty" }] },
  errors?: Record<string, string>,
) {
  const onValue = vi.fn<(value: Value) => void>();
  render(
    <Harness initial={initial} onValue={onValue} {...(errors === undefined ? {} : { errors })} />,
  );
  const last = () => onValue.mock.lastCall?.[0];
  return { user: userEvent.setup(), last };
}

describe("SchemaForm", () => {
  it("renders titled sections from the ui hint and puts the rest under Other", () => {
    setup();

    expect(screen.getAllByRole("heading", { level: 3 }).map((h) => h.textContent)).toEqual([
      "Story",
      "Sound",
      "Other",
    ]);
    expect(screen.getByLabelText(/Title/)).toHaveAccessibleDescription(/Shown on the video/);
  });

  it("edits text, enum, number and boolean fields", async () => {
    const { user, last } = setup();

    await user.clear(screen.getByLabelText(/Title/));
    await user.type(screen.getByLabelText(/Title/), "Sun");
    await user.selectOptions(screen.getByLabelText("Mood"), "funny");
    await user.type(screen.getByLabelText("Minutes"), "4");
    await user.click(screen.getByRole("switch", { name: "Background music" }));

    expect(last()).toMatchObject({ title: "Sun", mood: "funny", minutes: 4, music: true });
  });

  it("renders multi select arrays as checkboxes in enum order", async () => {
    const { user, last } = setup();

    await user.click(screen.getByRole("checkbox", { name: "sharing" }));
    await user.click(screen.getByRole("checkbox", { name: "kindness" }));

    expect(last()?.tags).toEqual(["kindness", "sharing"]);
  });

  it("adds, reorders and removes array items", async () => {
    const { user, last } = setup();
    const cast = within(screen.getByRole("group", { name: "Cast" }));

    await user.click(cast.getByRole("button", { name: "Add cast member" }));
    const names = cast.getAllByLabelText("Name");
    await user.type(names[1] as HTMLElement, "Mynah");
    await user.click(cast.getAllByRole("button", { name: "Move up" })[1] as HTMLElement);
    expect(last()?.cast).toEqual([{ name: "Mynah" }, { name: "Kutty" }]);

    await user.click(cast.getAllByRole("button", { name: "Remove" })[0] as HTMLElement);
    expect(last()?.cast).toEqual([{ name: "Kutty" }]);
  });

  it("shows external errors next to their fields, including nested ones", () => {
    setup(
      { title: "", cast: [{ name: "" }] },
      { title: "This field is required.", "cast.0.name": "Name taken." },
    );

    expect(screen.getByLabelText(/Title/)).toHaveAttribute("aria-invalid", "true");
    const alerts = screen.getAllByRole("alert").map((a) => a.textContent);
    expect(alerts).toEqual(expect.arrayContaining(["This field is required.", "Name taken."]));
  });
});
