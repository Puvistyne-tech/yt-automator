import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import {
  concealedBy,
  shownBy,
  visiblePathSet,
  withoutConcealed,
} from "@/shared/schema-form/fieldFilter";
import { SchemaForm } from "@/shared/schema-form/SchemaForm";
import { schemaFields } from "@/shared/schema-form/schemaFields";

const schema = {
  type: "object",
  properties: {
    title: { type: "string", title: "Title" },
    music: {
      type: "object",
      title: "Music",
      properties: {
        enabled: { type: "boolean", title: "Background music" },
        volume: { type: "number", title: "Volume" },
      },
    },
    cast: {
      type: "array",
      title: "Cast",
      items: { type: "object", properties: { name: { type: "string", title: "Name" } } },
    },
  },
};

const uiSchema = {
  "ui:sections": [
    { title: "Story", fields: ["title", "cast"] },
    { title: "Sound", fields: ["music"] },
  ],
};

const value = { title: "Moon", music: { enabled: true, volume: 0.3 }, cast: [{ name: "Ada" }] };
const defaults = { ...value, title: "Sun" };

const fields = schemaFields(schema);
const showing = (paths: string[]) => visiblePathSet(fields, shownBy(paths));

function hiding(paths: string[]) {
  const rule = withoutConcealed(undefined, concealedBy(fields, paths));
  return rule === undefined ? undefined : visiblePathSet(fields, rule);
}

function renderForm(visible?: ReadonlySet<string>, ui: Record<string, unknown> = uiSchema) {
  render(
    <SchemaForm
      idPrefix="s"
      schema={schema}
      uiSchema={ui}
      value={value}
      defaults={defaults}
      onChange={() => undefined}
      visible={visible}
    />,
  );
}

describe("SchemaForm visibility", () => {
  it("shows every field and section without a visibility rule", () => {
    renderForm();
    expect(screen.getByLabelText("Title")).toBeInTheDocument();
    expect(screen.getByLabelText("Volume")).toBeInTheDocument();
    expect(screen.getByText("1 changed")).toBeInTheDocument();
  });

  it("shows only visible children and hides sections left empty", () => {
    renderForm(showing(["music.enabled"]));
    expect(screen.getByRole("heading", { name: "Sound" })).toBeInTheDocument();
    expect(screen.getByLabelText("Background music")).toBeInTheDocument();
    expect(screen.queryByLabelText("Volume")).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Story" })).not.toBeInTheDocument();
    expect(screen.queryByText("1 changed")).not.toBeInTheDocument();
  });

  it("shows every child of a visible object", () => {
    renderForm(showing(["music"]));
    expect(screen.getByLabelText("Background music")).toBeInTheDocument();
    expect(screen.getByLabelText("Volume")).toBeInTheDocument();
    expect(screen.queryByLabelText("Title")).not.toBeInTheDocument();
  });

  it("shows whole array items under a visible array", () => {
    renderForm(showing(["cast"]));
    expect(screen.getByDisplayValue("Ada")).toBeInTheDocument();
    expect(screen.queryByLabelText("Title")).not.toBeInTheDocument();
  });

  it("filters an ungrouped form too", () => {
    renderForm(showing(["title"]), {});
    expect(screen.getByLabelText("Title")).toBeInTheDocument();
    expect(screen.queryByText("Music")).not.toBeInTheDocument();
  });

  it("leaves hidden settings out of the whole form", () => {
    renderForm(hiding(["music.volume", "title"]));
    expect(screen.getByLabelText("Background music")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Ada")).toBeInTheDocument();
    expect(screen.queryByLabelText("Volume")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Title")).not.toBeInTheDocument();
  });

  it("leaves out a whole group whose path is hidden", () => {
    renderForm(hiding(["music"]));
    expect(screen.queryByRole("heading", { name: "Sound" })).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Volume")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Title")).toBeInTheDocument();
  });

  it("leaves out a group whose every setting is hidden", () => {
    renderForm(hiding(["music.enabled", "music.volume"]));
    expect(screen.queryByRole("heading", { name: "Sound" })).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Background music")).not.toBeInTheDocument();
  });
});
