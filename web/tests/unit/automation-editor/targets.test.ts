import { makeAutomation, makeChannel, makeTarget } from "@/api/mocks/fixtures/factories";
import { kidsStoryPipeline } from "@/api/mocks/fixtures/pipeline";
import { draftFromAutomation } from "@/features/automation-editor/model/draft";
import {
  kidsFromValue,
  kidsValue,
  languageName,
  languageOptionsWithOrphan,
  orphanTargets,
  privacyOptions,
  targetChannelWarning,
  targetOptions,
  updateTarget,
  withoutOrphanTargets,
} from "@/features/automation-editor/model/targets";

const twoTargets = () =>
  draftFromAutomation(
    makeAutomation({
      languages: ["en"],
      targets: [makeTarget(), makeTarget({ id: "target-ta", language: "ta", playlist_id: "pl-1" })],
    }),
  );

describe("targetChannelWarning", () => {
  it.each([
    [undefined, null],
    [makeChannel(), null],
    [
      makeChannel({ title: "Old", status: "expired" }),
      "Old needs reconnecting on the Channels page before runs can publish to it.",
    ],
  ])("warns for %j", (channel, warning) => {
    expect(targetChannelWarning(channel)).toBe(warning);
  });
});

describe("target options", () => {
  it("offers channels with status, only selected languages and every variant", () => {
    const channels = [makeChannel(), makeChannel({ id: "c2", title: "Old", status: "expired" })];
    const options = targetOptions(kidsStoryPipeline, twoTargets(), channels);
    expect(options.channels.map((o) => o.label)).toEqual(["Bedtime tales", "Old (Token expired)"]);
    expect(options.languages).toEqual([{ value: "en", label: "English" }]);
    expect(options.variants.map((o) => o.label)).toEqual(["Episode · 16:9", "Short · 9:16"]);
    expect(options.kidsLocked).toBe(true);
    expect(options.addBlockedReason).toBeNull();
  });

  it.each([
    [[], ["en"], "Connect a YouTube channel first."],
    [[makeChannel()], [], "Choose at least one language first."],
  ])("explains why a target cannot be added", (channels, languages, reason) => {
    const draft = { ...twoTargets(), languages };
    expect(targetOptions(kidsStoryPipeline, draft, channels).addBlockedReason).toBe(reason);
  });

  it("names languages and keeps an orphan language visible", () => {
    expect(languageName(kidsStoryPipeline, "ta")).toBe("Tamil");
    expect(languageName(undefined, "xx")).toBe("xx");
    const options = [{ value: "en", label: "English" }];
    const orphan = twoTargets().targets[1];
    if (orphan === undefined) {
      throw new Error("missing target");
    }
    expect(languageOptionsWithOrphan(options, orphan, kidsStoryPipeline)).toEqual([
      ...options,
      { value: "ta", label: "Tamil (not selected)" },
    ]);
    expect(
      languageOptionsWithOrphan(options, { ...orphan, language: "en" }, kidsStoryPipeline),
    ).toBe(options);
    expect(languageOptionsWithOrphan(options, { ...orphan, language: "" }, kidsStoryPipeline)).toBe(
      options,
    );
  });
});

describe("target edits", () => {
  it("finds and drops targets whose language was removed", () => {
    const draft = twoTargets();
    expect(orphanTargets(draft.targets, draft.languages).map((t) => t.language)).toEqual(["ta"]);
    expect(withoutOrphanTargets(draft).targets.map((t) => t.language)).toEqual(["en"]);
  });

  it("clears the playlist when the channel changes", () => {
    const draft = twoTargets();
    const key = draft.targets[1]?.key ?? "";
    const same = updateTarget(draft, key, { channel_id: "chan-en", publish_delay_minutes: 5 });
    const moved = updateTarget(draft, key, { channel_id: "chan-ta" });
    expect(same.targets[1]).toMatchObject({ playlist_id: "pl-1", publish_delay_minutes: 5 });
    expect(moved.targets[1]).toMatchObject({ channel_id: "chan-ta", playlist_id: null });
    expect(moved.targets[0]).toBe(draft.targets[0]);
  });
});

describe("target choices", () => {
  it.each([
    [null, "default"],
    [true, "yes"],
    [false, "no"],
  ] as const)("maps made for kids %s to %s and back", (value, choice) => {
    expect(kidsValue(value)).toBe(choice);
    expect(kidsFromValue(choice)).toBe(value);
  });

  it("offers the channel default privacy first", () => {
    expect(privacyOptions(makeChannel()).map((o) => o.label)).toEqual([
      "Channel default (Private)",
      "Private",
      "Unlisted",
      "Public",
    ]);
    expect(privacyOptions(undefined)[0]).toEqual({ value: "", label: "Channel default" });
  });
});
