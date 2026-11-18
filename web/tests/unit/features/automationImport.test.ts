import { describe, expect, it } from "vitest";
import { ApiError } from "@/api/errors";
import { makeChannel } from "@/api/mocks/fixtures/factories";
import {
  CHOOSE_CHANNEL,
  channelChoiceOptions,
  channelMapFrom,
  fieldLabel,
  importProblem,
  LEAVE_OUT,
  parseExportFile,
} from "@/features/automation-list/importModel";

describe("parseExportFile", () => {
  it("accepts a JSON object", () => {
    expect(parseExportFile('{"app": "AutoTube"}')).toEqual({ document: { app: "AutoTube" } });
  });

  it.each(["not json", "[1, 2]", "null", '"text"'])("refuses %s", (text) => {
    expect(parseExportFile(text)).toEqual({
      error: "This file is not an automation export: it does not hold a JSON object.",
    });
  });
});

describe("channel choices", () => {
  it("offers connected channels and leaving the targets out", () => {
    const options = channelChoiceOptions([
      makeChannel(),
      makeChannel({ id: "chan-x", title: "Old", status: "revoked" }),
    ]);
    expect(options).toEqual([
      { value: "chan-en", label: "Bedtime tales" },
      { value: "chan-x", label: "Old (revoked)" },
      { value: LEAVE_OUT, label: "Leave its targets out" },
    ]);
  });

  it("sends chosen channels, null for leave out, and nothing for unchosen", () => {
    expect(channelMapFrom({ a: "chan-en", b: LEAVE_OUT, c: CHOOSE_CHANNEL })).toEqual({
      a: "chan-en",
      b: null,
    });
  });
});

describe("import problems", () => {
  it("labels document paths for people", () => {
    expect(fieldLabel("automation.settings.series.name.en")).toBe("Settings › series › name › en");
    expect(fieldLabel("automation.targets.0.language")).toBe("Targets › 1 › language");
    expect(fieldLabel("format_version")).toBe("Format version");
  });

  it("separates channel choices from other field errors", () => {
    const error = new ApiError(400, "validation_failed", "Validation failed", {
      "channel_map.gone": "choose a channel",
      "automation.pipeline_type": "unknown pipeline type 'x'",
    });
    expect(importProblem(error)).toEqual({
      message: null,
      channels: { gone: "choose a channel" },
      fields: [{ label: "Pipeline type", message: "unknown pipeline type 'x'" }],
    });
  });

  it("keeps a refusal message and a plain failure", () => {
    const refused = new ApiError(400, "validation_failed", "This file cannot be imported: newer.", {
      format_version: "newer",
    });
    expect(importProblem(refused)).toMatchObject({
      message: "This file cannot be imported: newer.",
      fields: [],
    });
    expect(importProblem(new Error("offline"))).toEqual({
      message: "offline",
      channels: {},
      fields: [],
    });
  });
});
