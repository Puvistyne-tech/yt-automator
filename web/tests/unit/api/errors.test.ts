import {
  ApiError,
  apiErrorFromBody,
  errorMessage,
  fieldErrorsOf,
  hasErrors,
  normalizeFieldErrors,
  normalizeFieldPath,
} from "@/api/errors";

describe("apiErrorFromBody", () => {
  it("reads code, message and string field errors from the error envelope", () => {
    const error = apiErrorFromBody(
      422,
      {
        error: { code: "invalid", message: "Check the form.", fields: { name: "Required", n: 3 } },
      },
      "fallback",
    );

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status: 422, code: "invalid", message: "Check the form." });
    expect(error.fields).toEqual({ name: "Required" });
  });

  it.each([null, "oops", { detail: "x" }, { error: [] }])(
    "falls back when the body is %j",
    (body) => {
      const error = apiErrorFromBody(502, body, "Bad gateway");
      expect(error).toMatchObject({ status: 502, code: "http_502", message: "Bad gateway" });
      expect(error.fields).toEqual({});
    },
  );
});

describe("apiErrorFromBody partial envelopes", () => {
  it.each([
    [{ error: { message: "m" } }, { code: "http_500", message: "m" }],
    [{ error: { code: "c" } }, { code: "c", message: "fb" }],
    [{ error: { code: 1, message: 2 } }, { code: "http_500", message: "fb" }],
  ])("falls back per field for %j", (body, expected) => {
    const error = apiErrorFromBody(500, body, "fb");
    expect(error).toMatchObject({ status: 500, ...expected });
    expect(error.fields).toEqual({});
  });
});

describe("error helpers", () => {
  it("knows whether a field error map has entries", () => {
    expect(hasErrors({})).toBe(false);
    expect(hasErrors({ name: "Required" })).toBe(true);
  });

  it("picks a readable message", () => {
    expect(errorMessage(new Error("Boom"))).toBe("Boom");
    expect(errorMessage(new Error(""))).toBe("Something went wrong. Please try again.");
    expect(errorMessage("string")).toBe("Something went wrong. Please try again.");
  });

  it("returns field errors only for API errors", () => {
    expect(fieldErrorsOf(new ApiError(422, "x", "y", { a: "b" }))).toEqual({ a: "b" });
    expect(fieldErrorsOf(new Error("x"))).toEqual({});
  });

  it.each([
    ["targets[0].channel_id", "targets.0.channel_id"],
    ["body.name", "name"],
    [".settings.cast[2].name", "settings.cast.2.name"],
    ["schedule.cron", "schedule.cron"],
  ])("normalizes %s to %s", (path, normalized) => {
    expect(normalizeFieldPath(path)).toBe(normalized);
  });

  it("normalizes every key of a field error map", () => {
    expect(normalizeFieldErrors({ "body.targets[1].language": "Bad" })).toEqual({
      "targets.1.language": "Bad",
    });
  });
});
