import type { RJSFSchema, RJSFValidationError } from "@rjsf/utils";
import { kidsStoryPipeline } from "@/api/mocks/fixtures/pipeline";
import { offersNotSet } from "@/shared/schema-form/choices";
import {
  messageFor,
  propertyToPath,
  scopedErrors,
  toErrorSchema,
  validateSchemaData,
} from "@/shared/schema-form/errors";
import { groupIntoSections, readSections } from "@/shared/schema-form/sections";

describe("schema form choices", () => {
  it.each([
    [true, {}, false],
    [true, { default: "auto" }, false],
    [false, { default: "auto" }, false],
    [undefined, { default: "auto" }, false],
    [false, {}, true],
    [undefined, { default: null }, true],
  ])("offers Not set when required is %s and the schema is %j: %s", (required, schema, offered) => {
    expect(offersNotSet(required, schema)).toBe(offered);
  });
});

const schema: RJSFSchema = {
  type: "object",
  required: ["title"],
  properties: {
    title: { type: "string", minLength: 2 },
    count: { type: "integer", minimum: 1 },
    cast: {
      type: "array",
      items: { type: "object", required: ["name"], properties: { name: { type: "string" } } },
    },
  },
};

describe("schema form errors", () => {
  it.each([
    [".title", "title"],
    [".cast.0.name", "cast.0.name"],
    ["['cast'][1]['name']", "cast.1.name"],
    ["/cast/2", "cast.2"],
    [undefined, ""],
  ])("turns property %j into path %j", (property, path) => {
    expect(propertyToPath(property)).toBe(path);
  });

  it("writes messages as sentences", () => {
    const error = (name: string, message: string): RJSFValidationError => ({
      name,
      message,
      stack: "",
    });
    expect(messageFor(error("required", "must have required property 'x'"))).toBe(
      "This field is required.",
    );
    expect(messageFor(error("minimum", "must be >= 1"))).toBe("Must be >= 1.");
    expect(messageFor(error("type", "Bad value!"))).toBe("Bad value!");
  });

  it("validates data and keeps the first message per path", () => {
    const errors = validateSchemaData(schema, { title: "x", count: 0, cast: [{}] });
    expect(Object.keys(errors).sort()).toEqual(["cast.0.name", "count", "title"]);
    expect(errors["cast.0.name"]).toBe("This field is required.");
    expect(validateSchemaData(schema, { title: "ok" })).toEqual({});
  });

  it("accepts the default settings of the fixture pipeline", () => {
    expect(
      validateSchemaData(kidsStoryPipeline.settings_schema, kidsStoryPipeline.default_settings),
    ).toEqual({});
  });

  it("scopes errors under a prefix", () => {
    const errors = {
      settings: "Bad",
      "settings.cast.0.name": "Required",
      "settings2.x": "No",
      name: "No",
    };
    expect(scopedErrors(errors, "settings")).toEqual({ "": "Bad", "cast.0.name": "Required" });
  });

  it("builds a nested error schema", () => {
    expect(toErrorSchema({ "": "Root", "cast.0.name": "Required", title: "Short" })).toEqual({
      __errors: ["Root"],
      cast: { 0: { name: { __errors: ["Required"] } } },
      title: { __errors: ["Short"] },
    });
  });
});

describe("schema form sections", () => {
  const props = ["a", "b", "c", "d"].map((name) => ({ name }));

  it("reads only well formed section hints", () => {
    expect(readSections(null)).toEqual([]);
    expect(readSections({ "ui:sections": "x" })).toEqual([]);
    expect(
      readSections({
        "ui:sections": [
          { title: "One", fields: ["a"] },
          { title: 2 },
          { title: "Bad", fields: [1] },
        ],
      }),
    ).toEqual([{ title: "One", fields: ["a"] }]);
  });

  it("returns one untitled section without hints", () => {
    expect(groupIntoSections(props, [])).toEqual([{ title: null, properties: props }]);
  });

  it("groups by hint order, drops empty sections and keeps the rest last", () => {
    const sections = groupIntoSections(props, [
      { title: "Story", fields: ["c", "a"] },
      { title: "Empty", fields: ["zzz"] },
    ]);
    expect(sections.map((s) => [s.title, s.properties.map((p) => p.name)])).toEqual([
      ["Story", ["c", "a"]],
      [null, ["b", "d"]],
    ]);
    expect(groupIntoSections(props, [{ title: "All", fields: ["a", "b", "c", "d"] }])).toHaveLength(
      1,
    );
  });
});
