import type { EngineSummary, SampleScene, SampleScript } from "@/api/types";
import { choiceOptions, defaultChoice } from "@/shared/schema-form/choices";

export interface EngineFormat {
  id: string;
  title: string;
}

interface FormatShape {
  title: (topic: string) => string;
  headings: string[];
  lines: (topic: string) => string[];
  takeaway: (topic: string) => string;
}

export interface SampleRequest {
  format: string;
  topic: string;
  language: string;
  provider: string;
}

const DEFAULT_TOPIC = "the night sky";

const ACTIONS = [
  "A slow pan across the opening picture",
  "The camera moves closer to the detail",
  "A gentle zoom out shows the whole scene",
  "The last picture holds still",
];

const explainerLines = (topic: string) => [
  `We see ${topic} often, but rarely stop to think about it.`,
  "It comes from a few simple forces working together.",
  "Up close, every part plays a small role in the whole.",
  `Knowing this changes how you notice ${topic} every day.`,
];

const EXPLAINER: FormatShape = {
  title: (topic) => `Understanding ${topic}`,
  headings: ["What it is", "Why it happens", "A closer look", "Why it matters"],
  lines: explainerLines,
  takeaway: (topic) => `Behind ${topic} are a few simple forces working together.`,
};

const SHAPES: Record<string, FormatShape> = {
  story: {
    title: (topic) => `The little lantern and ${topic}`,
    headings: [],
    lines: (topic) => [
      `Mina finds a small lantern by the river and wonders about ${topic}.`,
      "She asks the old owl, who tells her to look very closely.",
      "Together they follow the light and find something new.",
      "Mina walks home smiling, ready to share what she learned.",
    ],
    takeaway: () => "Curious questions lead to kind discoveries.",
  },
  explainer: EXPLAINER,
  list: {
    title: (topic) => `Four surprising facts about ${topic}`,
    headings: ["Fact 1", "Fact 2", "Fact 3", "Fact 4"],
    lines: (topic) => [
      `The oldest records of ${topic} are thousands of years old.`,
      "Most of it happens where nobody can see it.",
      "Scientists still argue about one part of it.",
      "You can spot it yourself with nothing but patience.",
    ],
    takeaway: () => "",
  },
  countdown: {
    title: (topic) => `Top four moments in ${topic}`,
    headings: ["Number 4", "Number 3", "Number 2", "Number 1"],
    lines: explainerLines,
    takeaway: () => "",
  },
  quiz: {
    title: (topic) => `Quick quiz: ${topic}`,
    headings: ["Question 1", "Question 2", "Question 3", "Answers"],
    lines: (topic) => [
      `How old are the first records of ${topic}?`,
      "Where does most of it happen?",
      "What do you need to spot it yourself?",
      "Thousands of years, out of sight, and patience.",
    ],
    takeaway: () => "",
  },
};

const FORMAT_FIELD = "structure";

export function engineFormats(engine: EngineSummary): EngineFormat[] {
  return choiceOptions(engine.definition_schema, FORMAT_FIELD).map((choice) => ({
    id: choice.value,
    title: choice.title,
  }));
}

export function defaultFormat(engine: EngineSummary): string {
  return defaultChoice(engine.definition_schema, FORMAT_FIELD) ?? "";
}

const NUMBERED_PARTS: FormatShape = {
  ...EXPLAINER,
  headings: EXPLAINER.headings.map((_heading, index) => `Part ${index + 1}`),
};

function shapeOf(format: string): FormatShape {
  return SHAPES[format] ?? NUMBERED_PARTS;
}

function scenesOf(shape: FormatShape, topic: string): SampleScene[] {
  return shape.lines(topic).map((narration, index) => ({
    narration,
    heading: shape.headings[index] ?? "",
    action: ACTIONS[index] ?? "",
  }));
}

export function sampleScript({ format, topic, language, provider }: SampleRequest): SampleScript {
  const shape = shapeOf(format);
  const subject = topic.trim() || DEFAULT_TOPIC;
  const scenes = scenesOf(shape, subject);
  const title = shape.title(subject);
  const takeaway = shape.takeaway(subject);
  const opening = scenes[0]?.narration ?? "";
  return {
    language,
    title,
    scenes,
    takeaway,
    upload_title: title,
    upload_description: `${opening}\n\n${takeaway || "Watch to the end for the answer."}`,
    provider,
  };
}
