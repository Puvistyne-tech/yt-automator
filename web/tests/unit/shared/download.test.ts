import { exportFileName } from "@/api/automations";
import { fileSlug } from "@/shared/download";

describe("fileSlug", () => {
  it.each([
    ["Bedtime stories", "bedtime-stories"],
    ["A/B: C?", "a-b-c"],
    ["  --x--  ", "x"],
    ["Café Crème", "cafe-creme"],
    ["கதை நேரம்", "untitled"],
    ["", "untitled"],
  ])("turns %j into %j", (text, slug) => {
    expect(fileSlug(text)).toBe(slug);
  });

  it("names export files after the automation", () => {
    expect(exportFileName({ name: "Story Time" })).toBe("story-time.autotube.json");
  });
});
